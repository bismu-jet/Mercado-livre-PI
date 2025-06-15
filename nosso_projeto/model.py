# -*- coding: utf-8 -*-
# ARQUIVO: model.py

from dataclasses import dataclass, field
from typing import Dict, List

@dataclass
class Order:
    """
    Representa um único pedido. Contém a estrutura de dados pura.
    """
    id: int
    items: Dict[int, int]
    total_units: int

@dataclass
class Aisle:
    """
    Representa um corredor no armazém.
    """
    id: int
    inventory: Dict[int, int]

@dataclass
class Instance:
    """
    Armazena todos os dados de uma instância do problema de forma estruturada.
    Esta classe é o contêiner central de dados do nosso modelo.
    """
    num_orders: int = 0
    num_items: int = 0
    num_aisles: int = 0
    orders: List[Order] = field(default_factory=list)
    aisles: List[Aisle] = field(default_factory=list)
    item_locations: Dict[int, List[int]] = field(default_factory=dict)
    orders_by_item: Dict[int, List[int]] = field(default_factory=dict) 
    min_wave_size: int = 0
    max_wave_size: int = 0

    def build_item_locations(self):
        """
        Constrói o mapeamento reverso de itens para corredores após o parsing.
        """
        self.item_locations.clear()
        for aisle in self.aisles:
            for item_id in aisle.inventory.keys():
                if item_id not in self.item_locations:
                    self.item_locations[item_id] = []
                self.item_locations[item_id].append(aisle.id)

    def build_orders_by_item(self):
        """
        Constrói o mapeamento reverso de itens para pedidos que os contêm.
        """
        self.orders_by_item.clear()
        for order in self.orders:
            for item_id in order.items:
                if item_id not in self.orders_by_item:
                    self.orders_by_item[item_id] = []
                self.orders_by_item[item_id].append(order.id)