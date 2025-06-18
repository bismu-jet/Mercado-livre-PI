# -*- coding: utf-8 -*-
# ARQUIVO: main.py

import sys
import gurobipy as gp
from data_parser import InstanceParser
from solver import WaveSolver
import logging

class StreamToLogger:
    """
    Redireciona um fluxo (como sys.stdout ou sys.stderr) para um logger.
    """
    def __init__(self, logger, level):
        self.logger = logger
        self.level = level
        self.linebuf = ''

    def write(self, buf):
        for line in buf.rstrip().splitlines():
            self.logger.log(self.level, line.rstrip())

    def flush(self):
        pass

# 2. Configura o logger principal
logging.basicConfig(
    level=logging.INFO, # Nível mínimo de mensagem a ser capturada (INFO, WARNING, ERROR)
    format='%(asctime)s - %(levelname)s - %(message)s', # Formato da mensagem
    filename='projeto_bess.log', # Nome do arquivo de log
    filemode='w' # 'w' para sobrescrever o arquivo a cada execução, 'a' para adicionar ao final
)

# 3. Adiciona um handler para também mostrar o log no console (opcional, mas recomendado)
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(logging.Formatter('%(asctime)s - %(message)s'))
logging.getLogger().addHandler(console_handler)

# 4. Redireciona o stdout (saída do print) para o nosso logger
stdout_logger = logging.getLogger('STDOUT')
sys.stdout = StreamToLogger(stdout_logger, logging.INFO)

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
    datasheet = 'a'
    #run_all = True
    run_all = True
    instance_case = '01'
    time_sec_setado = 300

    if run_all:
        if datasheet == 'a':
            loop_range = 20
        elif datasheet == 'b':
            loop_range = 15
        for i in range(1, loop_range+1):
            if i <= 9:
                instance_case = f'0{i}'
            else:
                instance_case = str(i)
            if len(sys.argv) < 3:
                print("Uso: python main.py <arquivo_de_entrada> <arquivo_de_saida> [limite_de_tempo_seg]")
                print("Usando valores padrão para um teste rápido...")
                input_f = f'../datasets/{datasheet}/instance_00{instance_case}.txt'
                output_f = f'../out_answers/{datasheet}/solucao_00{instance_case}.txt'
                time_sec = time_sec_setado # 5 minuto
            else:
                input_f = sys.argv[1]
                output_f = sys.argv[2]
                time_sec = int(sys.argv[3]) if len(sys.argv) > 3 else 600 # Padrão de 10 minutos
            print("=="*60)
            print(f'INSTANCIA {instance_case}')
            run_challenge(input_file=input_f, output_file=output_f, time_limit=time_sec)
            print(f'INSTANCIA {instance_case} ^^^^^^^^')
            print("=="*60)

    else:
        if len(sys.argv) < 3:
            print("Uso: python main.py <arquivo_de_entrada> <arquivo_de_saida> [limite_de_tempo_seg]")
            print("Usando valores padrão para um teste rápido...")
            input_f = f'../datasets/{datasheet}/instance_00{instance_case}.txt'
            output_f = f'../out_answers/{datasheet}/solucao_00{instance_case}.txt'
            time_sec = time_sec_setado # 5 minuto
        else:
            input_f = sys.argv[1]
            output_f = sys.argv[2]
            time_sec = int(sys.argv[3]) if len(sys.argv) > 3 else 600 # Padrão de 10 minutos

        print("=="*60)
        print(f'INSTANCIA {instance_case}')
        run_challenge(input_file=input_f, output_file=output_f, time_limit=time_sec)
        print(f'INSTANCIA {instance_case} ^^^^^^^^')
        print("=="*60)