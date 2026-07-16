from __future__ import annotations
from typing import TYPE_CHECKING

from .types.orders import Order
if TYPE_CHECKING: from .book_side import PriceTreeNode


class OrderNode:
    """
    Stores an order inside a price-level queue

    Attributes:
    - order: order stored by the node
    - prev: previous node in the queue
    - next: next node in the queue
    - tree_node: price-tree node containing this order
    """
    def __init__(
        self, 
        order: Order
    ) -> None:
        self.order = order
        self.prev: OrderNode | None = None
        self.next: OrderNode | None = None
        self.tree_node: PriceTreeNode | None = None
    

class PriceLevel:
    """
    Stores resting orders at a single price in FIFO order

    Attributes:
    - price: price shared by every order in the level
    - head: oldest order in the queue
    - tail: newest order in the queue
    - total_size: combined remaining size of all orders
    - order_count: number of orders in the price level
    """
    def __init__(
        self,
        price: int
    ) -> None:
        if not isinstance(price, int) or price <= 0:
            raise ValueError("Price must be a positive integer")

        self.price = price
        self.head: OrderNode | None = None
        self.tail: OrderNode | None = None
        self.total_size = 0
        self.order_count = 0

    def is_empty(self) -> bool:
        return self.order_count == 0
    
    def get_first(self) -> OrderNode | None:
        return self.head
    
    def get_last(self) -> OrderNode | None:
        return self.tail
    
    def append_node(self, node: OrderNode) -> None:
        """
        Adds an order to the back of the FIFO queue
        """
        if node.prev is not None or node.next is not None:
            raise ValueError("Node is already linked")
        
        if node is self.head or node is self.tail:
            raise ValueError("Node is already in this queue")

        if self.is_empty():
            # Add as head & tail
            self.head = node
            self.tail = node
        else:
            # Add to back of queue
            assert self.tail is not None
            self.tail.next = node
            node.prev = self.tail
            self.tail = node
        
        self.total_size += node.order.size
        self.order_count += 1

    def remove_node(self, node: OrderNode) -> None:
        """
        Removes an order from the FIFO queue
        """
        if node.tree_node is None:
            raise ValueError("Node is not resting in the book")

        if node.tree_node.price_level is not self:
            raise ValueError("Node does not belong to this price level")
        
        prev_node = node.prev
        next_node = node.next

        if node is self.head and node is self.tail:
            # 1 node in PL
            self.head = None
            self.tail = None
        
        elif node is self.head:
            # Node is the head
            assert next_node is not None
            self.head = next_node
            next_node.prev = None
        
        elif node is self.tail:
            # Node is the tail
            assert prev_node is not None
            self.tail = prev_node
            prev_node.next = None
        
        else:
            # Middle node
            assert prev_node is not None
            assert next_node is not None
            prev_node.next = next_node
            next_node.prev = prev_node
        
        node.prev = None
        node.next = None
        node.tree_node = None

        self.total_size -= node.order.size
        self.order_count -= 1

    def update_node_size(self, node: OrderNode, new_size: int) -> None:
        """
        Modifies the size of a resting order
        """
        old_size = node.order.size
        delta = new_size - old_size
        node.order.size = new_size

        self.total_size += delta
    
    def get_total_size(self) -> int:
        return self.total_size
    
    def get_order_count(self) -> int:
        return self.order_count
