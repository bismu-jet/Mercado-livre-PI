# -*- coding: utf-8 -*-
# ARQUIVO: main.py

import sys
import gurobipy as gp
from data_parser import InstanceParser
from solver import WaveSolver

def run_challenge(input_file: str, output_file: str, time_limit: int):
    """
    Função principal que orquestra a execução do desafio.
    
    1. Faz o parsing da instância.
    2. Cria e resolve o modelo de otimização.
    3. Salva a solução.
    """
    print("--- INICIANDO DESAFIO DE OTIMIZAÇÃO DE WAVE ---")
    try:
        # Etapa 1: Carregar os dados
        instance_data = InstanceParser.parse(input_file)

        # Etapa 2: Inicializar o solver com os dados
        solver = WaveSolver(instance_data, time_limit_sec=time_limit)

        # Etapa 3: Resolver o problema e salvar a solução
        solver.solve(output_file_path=output_file)

    except (FileNotFoundError, ValueError) as e:
        print(f"\nERRO DE ARQUIVO/DADOS: {e}")
    except gp.GurobiError as e:
        print(f"ERRO DO GUROBI: {e.errno} - {e.message}")
    except Exception as e:
        print(f"UM ERRO INESPERADO OCORREU: {e}")
    finally:
        print("\n--- EXECUÇÃO FINALIZADA ---")

if __name__ == '__main__':
    # Define os arquivos e o limite de tempo
    if len(sys.argv) < 3:
        print("Uso: python main.py <arquivo_de_entrada> <arquivo_de_saida> [limite_de_tempo_seg]")
        print("Usando valores padrão para um teste rápido...")
        input_f = './datasets/b/instance_0011.txt'
        output_f = './out_answers/b/solucao_0011.txt'
        time_sec = 300 # 5 minuto
    else:
        input_f = sys.argv[1]
        output_f = sys.argv[2]
        time_sec = int(sys.argv[3]) if len(sys.argv) > 3 else 600 # Padrão de 10 minutos
    
    run_challenge(input_file=input_f, output_file=output_f, time_limit=time_sec)