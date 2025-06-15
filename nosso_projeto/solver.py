# -*- coding: utf-8 -*-
# ARQUIVO: solver.py

import gurobipy as gp
from gurobipy import GRB

# Importa as entidades, mantendo o solver focado apenas na lógica de otimização.
from model import Instance

class WaveSolver:
    """
    Encapsula toda a lógica de modelagem e resolução do problema
    de otimização de waves usando Gurobi.
    """
    def __init__(self, instance: Instance, time_limit_sec: int = 600):
        self.instance = instance
        self.time_limit = time_limit_sec
        self.model = gp.Model("Optimal_Order_Selection")
        self.x = None
        self.y = None

    def _build_model(self):
        # (O conteúdo deste método permanece exatamente o mesmo de antes)
        print("Iniciando a construção do modelo matemático...")
        self.x = self.model.addVars((order.id for order in self.instance.orders), vtype=GRB.BINARY, name="x")
        self.y = self.model.addVars((aisle.id for aisle in self.instance.aisles), vtype=GRB.BINARY, name="y")

        z = self.model.addVar(vtype=GRB.CONTINUOUS, name="z_objective", lb=0.0)
        w = self.model.addVars((aisle.id for aisle in self.instance.aisles), vtype=GRB.CONTINUOUS, name="w", lb=0.0)

        self.model.setObjective(z, GRB.MAXIMIZE)
        print("Função objetivo definida: Maximizar z.")
        
        print("Adicionando restrições...")
        total_units_in_wave = gp.quicksum(order.total_units * self.x[order.id] for order in self.instance.orders)
        
        self.model.addConstr(w.sum() <= total_units_in_wave, "obj_linearization")

        M = self.instance.max_wave_size if self.instance.max_wave_size > 0 else 1e6
        for aisle in self.instance.aisles:
            a_id = aisle.id
            self.model.addConstr(w[a_id] <= M * self.y[a_id], f"bigM_w_upper_{a_id}")
            self.model.addConstr(w[a_id] <= z, f"bigM_w_z_upper_{a_id}")
            self.model.addConstr(w[a_id] >= z - M * (1 - self.y[a_id]), f"bigM_w_z_lower_{a_id}")

        self.model.addConstr(total_units_in_wave >= self.instance.min_wave_size, "min_wave_size")
        self.model.addConstr(total_units_in_wave <= self.instance.max_wave_size, "max_wave_size")
        
        all_item_ids = range(self.instance.num_items)
        for item_id in all_item_ids:
            demand = gp.quicksum(self.instance.orders[o].items.get(item_id, 0) * self.x[o] for o in range(self.instance.num_orders))
            supply = gp.quicksum(self.instance.aisles[a].inventory.get(item_id, 0) * self.y[a] for a in range(self.instance.num_aisles))
            self.model.addConstr(demand <= supply, f"inventory_sufficiency_{item_id}")
            
        print("Modelo construído com sucesso.")


    def _write_solution_file(self, output_path: str):
        print(f"Salvando solução em '{output_path}'...")
        selected_orders = [order.id for order in self.instance.orders if self.x[order.id].X > 0.5]
        visited_aisles = [aisle.id for aisle in self.instance.aisles if self.y[aisle.id].X > 0.5]
        with open(output_path, 'w') as f:
            f.write(f"{len(selected_orders)}\n")
            for order_id in selected_orders:
                f.write(f"{order_id}\n")
            f.write(f"{len(visited_aisles)}\n")
            for aisle_id in visited_aisles:
                f.write(f"{aisle_id}\n")
        print("Arquivo de solução salvo com sucesso.")

    def solve(self, output_file_path: str = None):
        # (O conteúdo deste método permanece exatamente o mesmo de antes)
        self._build_model()
        print(f"\nIniciando otimização com limite de tempo de {self.time_limit} segundos...")
        self.model.setParam('TimeLimit', self.time_limit)
        self.model.optimize()

        if self.model.Status == GRB.OPTIMAL or (self.model.Status == GRB.TIME_LIMIT and self.model.SolCount > 0):
            print("\n--- Solução Encontrada ---")
            selected_orders = [order.id for order in self.instance.orders if self.x[order.id].X > 0.5]
            visited_aisles = [aisle.id for aisle in self.instance.aisles if self.y[aisle.id].X > 0.5]
            total_units = sum(o.total_units for o in self.instance.orders if o.id in selected_orders)
            
            print(f"Status da Solução: {self.model.Status} (2=Ótima, 9=Limite de Tempo, etc.)")
            print(f"Valor da Função Objetivo (Densidade): {self.model.ObjVal:.4f}")
            print("-" * 25)
            print(f"Total de Pedidos na Wave: {len(selected_orders)}")
            print(f"Total de Unidades na Wave: {total_units}")
            print(f"Total de Corredores Visitados: {len(visited_aisles)}")
            
            if output_file_path:
                self._write_solution_file(output_file_path)
        elif self.model.Status == GRB.TIME_LIMIT:
            print("\nLimite de tempo atingido, mas nenhuma solução viável foi encontrada.")
        elif self.model.Status == GRB.INFEASIBLE:
            print("\nO modelo é inviável. Verifique as restrições.")
            self.model.computeIIS()
            self.model.write("model_iis.ilp")
            print("Um subconjunto de restrições conflitantes foi salvo em 'model_iis.ilp'")
        else:
            print(f"\nO processo de otimização terminou com o status: {self.model.Status}")