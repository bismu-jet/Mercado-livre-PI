# -*- coding: utf-8 -*-

from dataclasses import dataclass, field
from typing import Dict, List

@dataclass
class Order:
    """
    Representa um único pedido.

    Attributes:
        id (int): O identificador único do pedido.
        items (Dict[int, int]): Um dicionário mapeando ID do item para a quantidade solicitada.
        total_units (int): O número total de unidades neste pedido.
    """
    id: int
    items: Dict[int, int]
    total_units: int

@dataclass
class Aisle:
    """
    Representa um corredor no armazém.

    Attributes:
        id (int): O identificador único do corredor.
        inventory (Dict[int, int]): Dicionário mapeando ID do item para a quantidade disponível.
    """
    id: int
    inventory: Dict[int, int]

@dataclass
class Instance:
    """
    Armazena todos os dados de uma instância do problema de forma estruturada.
    O uso do decorador @dataclass simplifica a inicialização e representação da classe.
    """
    # --- Contagens Gerais ---
    num_orders: int = 0
    num_items: int = 0
    num_aisles: int = 0

    # --- Estruturas de Dados ---
    # Usamos field(default_factory=...) para garantir que cada nova instância 
    # tenha sua própria lista/dicionário, evitando armadilhas com mutáveis.
    orders: List[Order] = field(default_factory=list)
    aisles: List[Aisle] = field(default_factory=list)
    item_locations: Dict[int, List[int]] = field(default_factory=dict)

    # --- Restrições ---
    min_wave_size: int = 0
    max_wave_size: int = 0

    def build_item_locations(self):
        """
        Constrói o mapeamento reverso de itens para corredores após o parsing.
        Este é um pré-processamento para acelerar buscas futuras.
        """
        self.item_locations.clear()
        for aisle in self.aisles:
            for item_id in aisle.inventory.keys():
                if item_id not in self.item_locations:
                    self.item_locations[item_id] = []
                self.item_locations[item_id].append(aisle.id)


class InstanceParser:
    """
    Responsável por ler um arquivo de instância e carregar seus dados
    em um objeto `Instance` limpo e bem estruturado.
    Aderindo ao Princípio da Responsabilidade Única, esta classe faz uma
    coisa só: parsing.
    """
    @staticmethod
    def parse(file_path: str) -> Instance:
        """
        Lê um arquivo de instância e retorna um objeto Instance populado.

        Args:
            file_path (str): O caminho para o arquivo .txt da instância.

        Returns:
            Instance: Um objeto contendo todos os dados da instância.
        
        Raises:
            FileNotFoundError: Se o caminho do arquivo não for encontrado.
            ValueError: Se o arquivo tiver um formato inesperado.
        """
        print(f"Iniciando o parsing do arquivo: {file_path}")
        
        # A instância agora é um dataclass, sua inicialização é mais limpa.
        instance = Instance()
        
        with open(file_path, 'r') as f:
            lines = f.readlines()

        # 1. Ler o cabeçalho
        try:
            header = list(map(int, lines[0].strip().split()))
            instance.num_orders, instance.num_items, instance.num_aisles = header
            print(f"Cabeçalho lido: {instance.num_orders} pedidos, {instance.num_items} itens, {instance.num_aisles} corredores.")
        except (ValueError, IndexError) as e:
            raise ValueError(f"Erro ao ler o cabeçalho do arquivo. Detalhes: {e}")

        # 2. Ler o bloco de Pedidos
        current_line_index = 1
        for order_id in range(instance.num_orders):
            if current_line_index >= len(lines):
                raise ValueError(f"Arquivo terminou inesperadamente ao ler o pedido {order_id}.")
            
            parts = list(map(int, lines[current_line_index].strip().split()))
            k = parts[0]
            items_data = parts[1:]
            
            if len(items_data) != 2 * k:
                raise ValueError(f"Formato incorreto para o pedido {order_id} na linha {current_line_index + 1}.")
            
            order_items: Dict[int, int] = {}
            total_units = 0
            for i in range(k):
                item_id = items_data[2 * i]
                quantity = items_data[2 * i + 1]
                order_items[item_id] = quantity
                total_units += quantity
            
            instance.orders.append(Order(id=order_id, items=order_items, total_units=total_units))
            current_line_index += 1
        
        print(f"{len(instance.orders)} pedidos lidos com sucesso.")

        # 3. Ler o bloco de Corredores
        for aisle_id in range(instance.num_aisles):
            if current_line_index >= len(lines):
                 # Se a última linha (LB/UB) estiver faltando, isso é um aviso, não um erro fatal.
                print(f"Aviso: O arquivo parece não conter a seção de corredores completa ou a linha final de limites.")
                break

            parts = list(map(int, lines[current_line_index].strip().split()))
            l = parts[0]
            inventory_data = parts[1:]

            if len(inventory_data) != 2 * l:
                # Pode ser a linha final de limites, então paramos de ler corredores.
                break

            aisle_inventory: Dict[int, int] = {inventory_data[2*i]: inventory_data[2*i+1] for i in range(l)}
            instance.aisles.append(Aisle(id=aisle_id, inventory=aisle_inventory))
            current_line_index += 1
            
        print(f"{len(instance.aisles)} corredores lidos com sucesso.")

        # 4. Ler os limites da wave (a linha atual ou a próxima)
        if current_line_index < len(lines):
            try:
                limits = list(map(int, lines[current_line_index].strip().split()))
                if len(limits) == 2:
                    instance.min_wave_size, instance.max_wave_size = limits
                    print(f"Limites da wave lidos: LB={instance.min_wave_size}, UB={instance.max_wave_size}.")
                else:
                    print(f"Aviso: A última linha '{' '.join(map(str, limits))}' não parece ter o formato de limites (LB UB).")

            except (ValueError, IndexError) as e:
                print(f"Aviso: Não foi possível ler os limites da wave na última linha. Detalhes: {e}")
        else:
            print("Aviso: A linha de limites da wave (LB, UB) não foi encontrada no final do arquivo.")

        # 5. Pré-processamento final
        instance.build_item_locations()
        print("Mapeamento item -> corredor construído.")
        
        print("Parsing concluído com sucesso.")
        return instance

# --- Exemplo de Uso ---
if __name__ == '__main__':
    file_path = './datasets/a/instance_0014.txt'
    try:
        instance_data = InstanceParser.parse(file_path)

        # Verificando alguns dados para confirmar que o parsing funcionou
        print("\n--- Verificação dos Dados Carregados ---")
        print(f"Total de pedidos: {len(instance_data.orders)}")
        print(f"Total de corredores: {len(instance_data.aisles)}")
        print(f"Tamanho mínimo da wave: {instance_data.min_wave_size}")
        print(f"Tamanho máximo da wave: {instance_data.max_wave_size}")

        if instance_data.orders:
            # Exibe o primeiro e o último pedido lido
            print(f"Detalhes do Pedido 0: ID={instance_data.orders[0].id}, Itens={instance_data.orders[0].items}")
            last_order_idx = len(instance_data.orders) - 1
            print(f"Detalhes do Pedido {last_order_idx}: ID={instance_data.orders[last_order_idx].id}, Itens={instance_data.orders[last_order_idx].items}")
        
        if instance_data.aisles:
            # Exibe o primeiro corredor lido
             print(f"Inventário do Corredor 0 (primeiros 5 itens):")
             # Mostra apenas os primeiros 5 itens para não poluir a saída
             for i, (item, qty) in enumerate(instance_data.aisles[0].inventory.items()):
                 if i >= 5:
                     break
                 print(f"  Item {item}: {qty} unidades")
        
        # Verifica se o mapeamento reverso foi criado
        if instance_data.item_locations:
            item_id_example = list(instance_data.item_locations.keys())[0]
            print(f"Exemplo de mapeamento reverso: Item {item_id_example} está nos corredores: {instance_data.item_locations[item_id_example]}")


    except (FileNotFoundError, ValueError) as e:
        print(f"\nERRO: {e}")