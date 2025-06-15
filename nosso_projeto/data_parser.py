# -*- coding: utf-8 -*-
# ARQUIVO: data_parser.py

# Importa as entidades definidas no nosso novo módulo de modelo.
from model import Instance, Order, Aisle

class InstanceParser:
    """
    Responsável por ler um arquivo de instância e carregar seus dados
    em um objeto `Instance`.
    """
    @staticmethod
    def parse(file_path: str) -> Instance:
        """
        Lê um arquivo de instância e retorna um objeto Instance populado.
        """
        print(f"Iniciando o parsing do arquivo: {file_path}")
        
        instance = Instance()
        
        with open(file_path, 'r') as f:
            lines = f.readlines()

        # 1. Cabeçalho
        header = list(map(int, lines[0].strip().split()))
        instance.num_orders, instance.num_items, instance.num_aisles = header
        print(f"Cabeçalho lido: {instance.num_orders} pedidos, {instance.num_items} itens, {instance.num_aisles} corredores.")

        current_line_index = 1
        
        # 2. Pedidos
        for order_id in range(instance.num_orders):
            parts = list(map(int, lines[current_line_index].strip().split()))
            items_data = parts[1:]
            order_items = {items_data[2*i]: items_data[2*i+1] for i in range(parts[0])}
            total_units = sum(order_items.values())
            instance.orders.append(Order(id=order_id, items=order_items, total_units=total_units))
            current_line_index += 1
        print(f"{len(instance.orders)} pedidos lidos.")
        
        # 3. Corredores
        for aisle_id in range(instance.num_aisles):
            if current_line_index >= len(lines) or not lines[current_line_index].strip():
                break
            parts = list(map(int, lines[current_line_index].strip().split()))
            if len(parts) <= 2 and aisle_id > 0: # Provavelmente é a linha de limites
                 break
            inventory_data = parts[1:]
            aisle_inventory = {inventory_data[2*i]: inventory_data[2*i+1] for i in range(parts[0])}
            instance.aisles.append(Aisle(id=aisle_id, inventory=aisle_inventory))
            current_line_index += 1
        print(f"{len(instance.aisles)} corredores lidos.")

        # 4. Limites da Wave
        if current_line_index < len(lines):
            limits = list(map(int, lines[current_line_index].strip().split()))
            if len(limits) == 2:
                instance.min_wave_size, instance.max_wave_size = limits
                print(f"Limites da wave lidos: LB={instance.min_wave_size}, UB={instance.max_wave_size}.")

        # 5. Pós-processamento
        instance.build_item_locations()
        print("Mapeamento item -> corredor construído.")
        
        print("Parsing concluído.")
        return instance