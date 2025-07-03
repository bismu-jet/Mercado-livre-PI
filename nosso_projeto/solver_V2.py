# -*- coding: utf-8 -*-
# ARQUIVO: solver_v7_dinkelbach_final.py
# DESCRIÇÃO: Versão final com gestão de tempo por iteração para garantir
#            progresso constante e evitar travamentos.

import gurobipy as gp
from gurobipy import GRB
from typing import Dict, Tuple, List
import time

# Importa as entidades, mantendo o solver focado apenas na lógica de otimização.
from model import Instance

class WaveSolver:
    """
    Encapsula a lógica de resolução usando o Algoritmo de Dinkelbach com
    gestão de tempo por iteração, a abordagem mais robusta para este problema.
    """

    def __init__(self, instance: Instance, time_limit_sec: int = 600):
        self.instance = instance
        self.time_limit = time_limit_sec
        self.best_solution = {
            "orders": [], "aisles": [], "objective": 0.0, "total_units": 0
        }

    def _generate_initial_solution(self) -> Tuple[float, List[int], List[int]]:
        """
        Executa a heurística gulosa e VALIDA sua viabilidade para gerar uma
        solução inicial de alta qualidade.
        """
        print("Executando heurística gulosa para obter ponto de partida...")
        
        order_scores = []
        for order in self.instance.orders:
            required_aisles = set()
            for item_id in order.items:
                if item_id in self.instance.item_locations:
                    required_aisles.update(self.instance.item_locations[item_id])
            
            num_required_aisles = len(required_aisles)
            if num_required_aisles > 0:
                score = order.total_units / num_required_aisles
                order_scores.append((score, order))

        order_scores.sort(key=lambda item: item[0], reverse=True)

        selected_orders_set = set()
        current_units = 0
        for _, order in order_scores:
            if current_units + order.total_units <= self.instance.max_wave_size:
                selected_orders_set.add(order.id)
                current_units += order.total_units
        
        if current_units < self.instance.min_wave_size:
            print("Solução heurística inválida (não atingiu o tamanho mínimo). Começando com ratio = 0.")
            return 0.0, [], []

        heuristic_aisles_set = set()
        all_items_in_heuristic_wave = set()
        for order_id in selected_orders_set:
            order = self.instance.orders[order_id]
            all_items_in_heuristic_wave.update(order.items.keys())
            for item_id in order.items:
                if item_id in self.instance.item_locations:
                    heuristic_aisles_set.update(self.instance.item_locations[item_id])
        
        if not heuristic_aisles_set:
             return 0.0, [], []

        for item_id in all_items_in_heuristic_wave:
            demand = sum(self.instance.orders[o_id].items.get(item_id, 0) for o_id in selected_orders_set)
            supply = sum(self.instance.aisles[a_id].inventory.get(item_id, 0) for a_id in heuristic_aisles_set)
            if demand > supply:
                print(f"Heurística gerou solução INVIÁVEL para item {item_id}. Descartando.")
                return 0.0, [], []

        initial_ratio = current_units / len(heuristic_aisles_set)
        print(f"Solução heurística VIÁVEL encontrou ratio inicial: {initial_ratio:.4f}")
        
        selected_orders = list(selected_orders_set)
        visited_aisles = list(heuristic_aisles_set)

        self.best_solution = {
            "orders": selected_orders,
            "aisles": visited_aisles,
            "objective": initial_ratio,
            "total_units": current_units
        }
        return initial_ratio, selected_orders, visited_aisles

    def _solve_subproblem(self, ratio_R: float, time_limit_iter: float, warm_start_orders: List[int], warm_start_aisles: List[int]):
        """
        Resolve o subproblema linear para um dado ratio R, com limite de tempo e warm start.
        """
        sub_model = gp.Model(f"subproblem_R_{ratio_R:.4f}")
        sub_model.setParam('OutputFlag', 0)

        x = sub_model.addVars((order.id for order in self.instance.orders), vtype=GRB.BINARY, name="x")
        y = sub_model.addVars((aisle.id for aisle in self.instance.aisles), vtype=GRB.BINARY, name="y")

        if warm_start_orders:
            sub_model.update()
            for order_id in warm_start_orders:
                x[order_id].Start = 1.0
        if warm_start_aisles:
            sub_model.update()
            for aisle_id in warm_start_aisles:
                y[aisle_id].Start = 1.0

        total_units_expr = gp.quicksum(order.total_units * x[order.id] for order in self.instance.orders)
        total_aisles_expr = y.sum()
        sub_model.setObjective(total_units_expr - ratio_R * total_aisles_expr, GRB.MAXIMIZE)

        sub_model.addConstr(total_units_expr >= self.instance.min_wave_size, "min_wave_size")
        sub_model.addConstr(total_units_expr <= self.instance.max_wave_size, "max_wave_size")

        orders_by_item = self.instance.orders_by_item
        aisles_by_item = self.instance.item_locations
        for item_id, relevant_orders in orders_by_item.items():
            demand = gp.quicksum(self.instance.orders[o_id].items[item_id] * x[o_id] for o_id in relevant_orders)
            relevant_aisles = aisles_by_item.get(item_id, [])
            supply = gp.quicksum(self.instance.aisles[a_id].inventory.get(item_id, 0) * y[a_id] for a_id in relevant_aisles)
            sub_model.addConstr(demand <= supply, f"inventory_sufficiency_{item_id}")

        sub_model.setParam('TimeLimit', time_limit_iter)
        sub_model.setParam('MIPFocus', 1)
        sub_model.setParam('Heuristics', 0.2)
        
        sub_model.optimize()

        if sub_model.SolCount > 0:
            selected_orders = [o.id for o in self.instance.orders if x[o.id].X > 0.5]
            visited_aisles = [a.id for a in self.instance.aisles if y[a.id].X > 0.5]
            return sub_model.ObjVal, selected_orders, visited_aisles
        
        return -float('inf'), [], []


    def _write_solution_file(self, output_path: str):
        print(f"Salvando a melhor solução encontrada em '{output_path}'...")
        sol = self.best_solution
        with open(output_path, 'w') as f:
            f.write(f"{len(sol['orders'])}\n")
            for order_id in sorted(sol['orders']):
                f.write(f"{order_id}\n")
            f.write(f"{len(sol['aisles'])}\n")
            for aisle_id in sorted(sol['aisles']):
                f.write(f"{aisle_id}\n")
        print("Arquivo de solução salvo com sucesso.")

    def solve(self, output_file_path: str = None):
        start_time = time.time()
        print("\n--- INICIANDO SOLVER COM ALGORITMO DE DINKELBACH (GESTÃO DE TEMPO) ---")

        current_R, last_orders, last_aisles = self._generate_initial_solution()
        
        MAX_ITERATIONS = 25
        CONVERGENCE_TOL = 1e-6
        
        # --- GESTÃO DE TEMPO POR ITERAÇÃO (LÓGICA FINAL) ---
        # Aloca um tempo fixo para a primeira, e mais fácil, iteração.
        time_for_first_iteration = 30 
        # Divide o tempo restante entre as outras iterações.
        remaining_time_for_others = self.time_limit - time_for_first_iteration
        time_per_iteration = max(15, remaining_time_for_others / (MAX_ITERATIONS -1)) if MAX_ITERATIONS > 1 else remaining_time_for_others
        print(f"Estratégia de tempo: {time_for_first_iteration}s para a 1ª iteração, até {time_per_iteration:.1f}s para as seguintes.")


        for i in range(MAX_ITERATIONS):
            elapsed_time = time.time() - start_time
            if elapsed_time >= self.time_limit - 5: # Deixa uma margem de segurança
                print("Tempo limite global atingido. Finalizando.")
                break

            iter_time_limit = time_for_first_iteration if i == 0 else time_per_iteration
            
            print(f"\n--- Iteração {i+1} (Ratio Atual = {current_R:.6f}, Limite de Tempo = {iter_time_limit:.1f}s) ---")
            
            F_R, new_orders, new_aisles = self._solve_subproblem(current_R, iter_time_limit, last_orders, last_aisles)

            if F_R <= CONVERGENCE_TOL:
                print(f"Convergência atingida. F(R) = {F_R:.6f} <= {CONVERGENCE_TOL}.")
                break
            
            total_units = sum(self.instance.orders[o_id].total_units for o_id in new_orders)
            num_aisles = len(new_aisles)

            if num_aisles == 0:
                print("Subproblema retornou uma solução com zero corredores. Interrompendo.")
                break
            
            new_R = total_units / num_aisles
            
            # Apenas atualiza se a nova solução for estritamente melhor
            if new_R > current_R + CONVERGENCE_TOL:
                 print(f"Solução melhorada encontrada. Novo Ratio = {new_R:.6f}")
                 self.best_solution = {
                    "orders": new_orders,
                    "aisles": new_aisles,
                    "objective": new_R,
                    "total_units": total_units
                 }
                 current_R = new_R
                 last_orders, last_aisles = new_orders, new_aisles
            else:
                print("Nenhuma melhoria significativa encontrada nesta iteração. Finalizando.")
                break
        
        print("\n--- Processo de Otimização Finalizado ---")
        sol = self.best_solution
        if sol["objective"] > 0:
            print(f"Melhor Solução Encontrada:")
            print(f"Valor da Função Objetivo REAL (Densidade): {sol['objective']:.4f}")
            print("-" * 25)
            print(f"Total de Pedidos na Wave: {len(sol['orders'])}")
            print(f"Total de Unidades na Wave: {sol['total_units']}")
            print(f"Total de Corredores Visitados: {len(sol['aisles'])}")
            
            if output_file_path:
                self._write_solution_file(output_file_path)
        else:
            print("Nenhuma solução viável com objetivo positivo foi encontrada.")
