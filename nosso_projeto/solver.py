# -*- coding: utf-8 -*-
# ARQUIVO: solver.py

import gurobipy as gp
from gurobipy import GRB
from typing import Dict, Tuple

# Importa as entidades, mantendo o solver focado apenas na lógica de otimização.
from model import Instance

class WaveSolver:
    """
    Encapsula toda a lógica de modelagem e resolução do problema
    de otimização de waves usando Gurobi.
    Inclui uma heurística para gerar uma solução inicial (Warm Start).
    """

    def __init__(self, instance: Instance, time_limit_sec: int = 600):
        """
        Inicializa o solver com os dados da instância e configurações.
        """
        self.instance = instance
        self.time_limit = time_limit_sec
        self.model = gp.Model("Optimal_Order_Selection")
        self.x = None
        self.y = None

    def _generate_warm_start(self) -> Tuple[Dict, Dict]:
        """
        Gera uma solução inicial de alta qualidade usando uma heurística gulosa.
        O objetivo é dar ao Gurobi um "Warm Start" para acelerar a otimização.

        A heurística funciona da seguinte forma:
        1. Calcula uma "pontuação de densidade" para cada pedido.
        2. Ordena os pedidos pela maior pontuação (mais unidades em menos corredores).
        3. Adiciona iterativamente os melhores pedidos a uma wave, desde que os
           limites de tamanho (UB) não sejam violados.
        4. Retorna uma solução inicial (dicionários para as variáveis x e y).
        """
        print("Executando heurística gulosa...")
        
        # 1. Calcular a pontuação de densidade para cada pedido
        order_scores = []
        for order in self.instance.orders:
            # Encontra o conjunto de corredores únicos necessários para este pedido
            required_aisles = set()
            for item_id in order.items:
                if item_id in self.instance.item_locations:
                    required_aisles.update(self.instance.item_locations[item_id])
            
            num_required_aisles = len(required_aisles)
            if num_required_aisles > 0:
                # Pontuação: unidades por corredor. Adicionamos um pequeno epsilon
                # para evitar divisão por zero e favorecer pedidos com mais unidades em caso de empate.
                score = order.total_units / num_required_aisles
                order_scores.append((score, order))

        # 2. Ordenar pedidos pela pontuação, do maior para o menor
        order_scores.sort(key=lambda item: item[0], reverse=True)

        # 3. Construir a wave de forma gulosa
        selected_orders_set = set()
        current_units = 0
        for score, order in order_scores:
            if current_units + order.total_units <= self.instance.max_wave_size:
                selected_orders_set.add(order.id)
                current_units += order.total_units
        
        # 4. Verificar se a solução heurística é minimamente válida
        if current_units < self.instance.min_wave_size:
            print("Solução heurística não atingiu o tamanho mínimo da wave. Nenhum Warm Start será usado.")
            return {}, {}

        # 5. Preparar os dicionários de start para o Gurobi
        start_x = {}
        start_y = {}
        heuristic_aisles = set()

        for order in self.instance.orders:
            if order.id in selected_orders_set:
                start_x[order.id] = 1.0
                # Acumula os corredores necessários para a solução heurística
                for item_id in order.items:
                    if item_id in self.instance.item_locations:
                        heuristic_aisles.update(self.instance.item_locations[item_id])
            else:
                start_x[order.id] = 0.0

        for aisle in self.instance.aisles:
            if aisle.id in heuristic_aisles:
                start_y[aisle.id] = 1.0
            else:
                start_y[aisle.id] = 0.0

        return start_x, start_y


    def _build_model(self):
        """
        Constrói o modelo matemático do Gurobi (variáveis, restrições e objetivo).
        """
        # (O conteúdo deste método permanece inalterado)
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
        
#        all_item_ids = range(self.instance.num_items)
#        for item_id in all_item_ids:
#            demand = gp.quicksum(self.instance.orders[o].items.get(item_id, 0) * self.x[o] for o in range(self.instance.num_orders))
#            supply = gp.quicksum(self.instance.aisles[a].inventory.get(item_id, 0) * self.y[a] for a in range(self.instance.num_aisles))
#            self.model.addConstr(demand <= supply, f"inventory_sufficiency_{item_id}")
        # d) Restrição de Suficiência de Inventário (OTIMIZADA)
        #    Agora, iteramos apenas sobre os itens que de fato existem em algum pedido.
        #    Para cada item, construímos as somas de demanda e oferta
        #    usando apenas os pedidos e corredores relevantes que o possuem.
        
        # O 'dossiê' dos pedidos que contêm cada item.
        orders_by_item = self.instance.orders_by_item
        # O 'dossiê' dos corredores que contêm cada item.
        aisles_by_item = self.instance.item_locations

        # Iteramos apenas sobre os itens que são demandados, usando nosso dossiê.
        for item_id, relevant_orders in orders_by_item.items():
            
            # Demanda: A soma é feita apenas sobre os pedidos relevantes.
            demand = gp.quicksum(self.instance.orders[o_id].items[item_id] * self.x[o_id] for o_id in relevant_orders)
            
            # Oferta: A soma é feita apenas sobre os corredores relevantes.
            # Usamos .get() pois um item pode ser demandado mas não ter estoque em lugar nenhum.
            relevant_aisles = aisles_by_item.get(item_id, [])
            supply = gp.quicksum(self.instance.aisles[a_id].inventory[item_id] * self.y[a_id] for a_id in relevant_aisles)
            
            # A restrição permanece a mesma, mas é construída de forma infinitamente mais rápida.
            self.model.addConstr(demand <= supply, f"inventory_sufficiency_{item_id}")
            
        print("Modelo construído com sucesso.")


    def _write_solution_file(self, output_path: str):
        """
        Escreve a solução encontrada no formato especificado pelo desafio.
        """
        # (O conteúdo deste método permanece inalterado)
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
        """
        Constrói o modelo, gera um warm start, otimiza e salva os resultados.
        """
        self._build_model()
        
        # --- ETAPA DE WARM START (NOVA LÓGICA) ---
        print("\nGerando uma solução inicial com heurística gulosa...")
        start_x, start_y = self._generate_warm_start()
        
        if start_x:
            print("Solução inicial encontrada. Fornecendo ao Gurobi (Warm Start).")
            for o_id, val in start_x.items():
                self.x[o_id].Start = val
            for a_id, val in start_y.items():
                self.y[a_id].Start = val
        else:
            print("Heurística não produziu uma solução inicial.")
        # --- FIM DA ETAPA DE WARM START ---

        print(f"\nIniciando otimização com limite de tempo de {self.time_limit} segundos...")
        self.model.setParam('TimeLimit', self.time_limit)

        print("Ajustando parâmetros do Gurobi para um ataque rápido...")
        
        # Foco em encontrar soluções viáveis de alta qualidade.
        self.model.setParam('MIPFocus', 1)
        
        # Aloca 10% do tempo para heurísticas internas.
        self.model.setParam('Heuristics', 0.1)
        
        # Usa os primeiros 300 segundos para tentar melhorar a solução do Warm Start.
        self.model.setParam('ImproveStartTime', 100)

        self.model.optimize()

        # (O bloco de análise e escrita de resultados permanece o mesmo)
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