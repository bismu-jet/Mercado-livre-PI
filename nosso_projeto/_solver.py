# -*- coding: utf-8 -*-

import sys
import gurobipy as gp
from gurobipy import GRB

# Importamos as classes do nosso parser de dados.
from parser import Instance, InstanceParser

class WaveSolver:
    """
    Encapsula toda a lógica de modelagem e resolução do problema
    de otimização de waves usando Gurobi.
    """

    def __init__(self, instance: Instance, time_limit_sec: int = 600):
        """
        Inicializa o solver com os dados da instância e configurações.

        Args:
            instance (Instance): O objeto com os dados carregados do problema.
            time_limit_sec (int): O limite de tempo para a execução do solver em segundos.
        """
        self.instance = instance
        self.time_limit = time_limit_sec
        self.model = gp.Model("Optimal_Order_Selection")
        
        # Atributos para armazenar as variáveis de decisão do Gurobi
        self.x = None
        self.y = None

    def _build_model(self):
        """
        Constrói o modelo matemático do Gurobi (variáveis, restrições e objetivo).
        """
        print("Iniciando a construção do modelo matemático...")

        # --- 1. VARIÁVEIS DE DECISÃO ---
        # As variáveis agora são salvas como atributos de instância (self.x, self.y)
        
        # x_o: binária, 1 se o pedido 'o' for selecionado.
        self.x = self.model.addVars((order.id for order in self.instance.orders), vtype=GRB.BINARY, name="x")

        # y_a: binária, 1 se o corredor 'a' for visitado.
        self.y = self.model.addVars((aisle.id for aisle in self.instance.aisles), vtype=GRB.BINARY, name="y")

        # --- 2. VARIÁVEIS PARA LINEARIZAÇÃO DO OBJETIVO ---
        z = self.model.addVar(vtype=GRB.CONTINUOUS, name="z_objective", lb=0.0)
        w = self.model.addVars((aisle.id for aisle in self.instance.aisles), vtype=GRB.CONTINUOUS, name="w", lb=0.0)

        # --- 3. FUNÇÃO OBJETIVO ---
        self.model.setObjective(z, GRB.MAXIMIZE)
        print("Função objetivo definida: Maximizar z.")

        # --- 4. RESTRIÇÕES ---
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
            demand = gp.quicksum(order.items.get(item_id, 0) * self.x[order.id] for order in self.instance.orders)
            supply = gp.quicksum(aisle.inventory.get(item_id, 0) * self.y[aisle.id] for aisle in self.instance.aisles)
            self.model.addConstr(demand <= supply, f"inventory_sufficiency_{item_id}")

        print("Modelo construído com sucesso.")

    def _write_solution_file(self, output_path: str):
        """
        Escreve a solução encontrada no formato especificado pelo desafio. 

        Args:
            output_path (str): O caminho do arquivo onde a solução será salva.
        """
        print(f"Salvando solução em '{output_path}'...")
        
        selected_orders = [order.id for order in self.instance.orders if self.x[order.id].X > 0.5]
        visited_aisles = [aisle.id for aisle in self.instance.aisles if self.y[aisle.id].X > 0.5]

        with open(output_path, 'w') as f:
            # Primeira linha: número de pedidos na wave 
            f.write(f"{len(selected_orders)}\n")
            
            # Próximas n linhas: índice de cada pedido 
            for order_id in selected_orders:
                f.write(f"{order_id}\n")
            
            # Linha seguinte: número de corredores visitados 
            f.write(f"{len(visited_aisles)}\n")
            
            # Próximas m linhas: índice de cada corredor 
            for aisle_id in visited_aisles:
                f.write(f"{aisle_id}\n")
        
        print("Arquivo de solução salvo com sucesso.")


    def solve(self, output_file_path: str = None):
        """
        Constrói e otimiza o modelo, depois exibe e salva os resultados.

        Args:
            output_file_path (str, optional): Se fornecido, salva a solução neste arquivo.
        """
        self._build_model()

        print(f"\nIniciando otimização com limite de tempo de {self.time_limit} segundos...")
        self.model.setParam('TimeLimit', self.time_limit)
        self.model.optimize()

        # --- 5. ANÁLISE E ESCRITA DOS RESULTADOS ---
        if self.model.Status == GRB.OPTIMAL or (self.model.Status == GRB.TIME_LIMIT and self.model.SolCount > 0):
            print("\n--- Solução Encontrada ---")
            
            # Corrigido: usando self.x e self.y
            selected_orders = [order.id for order in self.instance.orders if self.x[order.id].X > 0.5]
            visited_aisles = [aisle.id for aisle in self.instance.aisles if self.y[aisle.id].X > 0.5]
            
            total_units = sum(o.total_units for o in self.instance.orders if o.id in selected_orders)
            
            print(f"Status da Solução: {self.model.Status} (2=Ótima, 9=Limite de Tempo, etc.)")
            print(f"Valor da Função Objetivo (Densidade): {self.model.ObjVal:.4f}")
            print("-" * 25)
            print(f"Total de Pedidos na Wave: {len(selected_orders)}")
            print(f"Total de Unidades na Wave: {total_units}")
            print(f"Total de Corredores Visitados: {len(visited_aisles)}")
            
            # Salva a solução se um caminho de arquivo foi fornecido
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


# --- Bloco de Execução Principal ---
if __name__ == '__main__':
    # Tornando o script mais flexível com argumentos de linha de comando
    if len(sys.argv) < 2:
        print("Uso: python solver.py <caminho_para_instancia> [caminho_para_solucao_saida]")
        # Para facilitar, usamos um valor padrão se nenhum argumento for passado
        input_file = './datasets/b/instance_0001.txt'
        output_file = './out_answers/b/solucao_0001.txt'
        print(f"Usando arquivos padrão: '{input_file}' e '{output_file}'")
    else:
        input_file = sys.argv[1]
        output_file = sys.argv[2] if len(sys.argv) > 2 else f"solucao_{input_file.split('/')[-1]}"

    try:
        # 1. Carregar os dados
        instance_data = InstanceParser.parse(input_file)

        # 2. Inicializar o solver
        solver = WaveSolver(instance_data, time_limit_sec=60)

        # 3. Resolver e salvar a solução
        solver.solve(output_file_path=output_file)

    except (FileNotFoundError, ValueError) as e:
        print(f"\nERRO: {e}")
    except gp.GurobiError as e:
        print(f"Erro do Gurobi: {e.errno} - {e.message}")