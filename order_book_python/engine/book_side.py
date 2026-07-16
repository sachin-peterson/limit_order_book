from __future__ import annotations

from .price_level import OrderNode, PriceLevel
from .types.enums import Side


class PriceTreeNode:
    """
    Stores a price level inside the book_side price tree

    Attributes:
    - price_level: price level stored by the node
    - left: child containing lower prices
    - right: child containing higher prices
    - parent: parent node in the tree
    """
    def __init__(
        self,
        price_level: PriceLevel
    ) -> None:
        self.price_level = price_level
        self.left: PriceTreeNode | None = None
        self.right: PriceTreeNode | None = None
        self.parent: PriceTreeNode | None = None


class BookSide:
    """
    Stores one side of the order book as a price-level tree

    Attributes:
    - side: "BUY" or "SELL" side represented by the tree
    - root: root node of the price tree
    - best: node containing the best available price
    """
    def __init__(
        self,
        side: Side
    ) -> None:
        if not isinstance(side, Side):
            raise ValueError("Side must be BUY or SELL")

        self.side = side
        self.root: PriceTreeNode | None = None
        self.best: PriceTreeNode | None = None

    def is_empty(self) -> bool:
        return self.root is None

    def get_best_price(self) -> int | None:
        """
        Queries the best price
        """
        return None if self.best is None else self.best.price_level.price

    def get_best_level(self) -> PriceLevel | None:
        """
        Queries the best price level
        """
        return None if self.best is None else self.best.price_level

    def get_best_node(self) -> PriceTreeNode | None:
        """
        Queries the best price node
        """
        return self.best
    
    def get_maximum_node(self, start_node: PriceTreeNode) -> PriceTreeNode:
        """
        Finds the maximum node in the BST
        """
        curr = start_node
        while curr.right is not None:
            curr = curr.right
        
        return curr

    def get_minimum_node(self, start_node: PriceTreeNode) -> PriceTreeNode:
        """
        Finds the minimum node in the BST
        """
        curr = start_node
        while curr.left is not None:
            curr = curr.left
        
        return curr
    
    def get_price_level(self, price: int) -> PriceTreeNode | None:
        """
        Searches the BST for a given price level
        """
        # If the BST is empty, return None
        if self.is_empty():
            return None
        
        # Otherwise, search the BST for the PL
        curr = self.root
        while curr is not None:
            if curr.price_level.price == price:
                return curr
            elif curr.price_level.price > price:
                curr = curr.left
            elif curr.price_level.price < price:
                curr = curr.right
        
        return None
    
    def insert_price_level(self, price: int) -> PriceTreeNode:
        """
        Inserts a new price level into the BST
        """
        if self.get_price_level(price) is not None:
            raise ValueError(f"Price level {price} already exists")
    
        # Create the price level
        price_level = PriceLevel(price)
        new_node = PriceTreeNode(price_level)

        # If the BST is empty, create a new BST
        if self.is_empty():
            self.root = new_node
            self.best = new_node
            return new_node
        
        # Otherwise, insert the PL into the BST
        current = self.root
        while current is not None:
            if current.price_level.price > price and current.left is not None:
                current = current.left
            elif current.price_level.price < price and current.right is not None:
                current = current.right
            else:
                break

        # Insert the PL into the correct position
        assert current is not None
        if current.price_level.price > price:
            current.left = new_node
        else:
            current.right = new_node
        
        new_node.parent = current

        self.update_best_after_insertion(new_node)

        return new_node

    def update_best_after_insertion(self, new_node: PriceTreeNode) -> None:
        """
        Updates the best bid/ask after PL insertion
        """
        if self.best is None:
            self.best = new_node
        if self.side is Side.BUY and new_node.price_level.price > self.best.price_level.price:
            self.best = new_node
        if self.side == Side.SELL and new_node.price_level.price < self.best.price_level.price:
            self.best = new_node
        
    def remove_price_level(self, node: PriceTreeNode) -> None:
        """
        Removes a price level from the BST
        """
        if not node.price_level.is_empty():
            raise ValueError("Cannot remove a non-empty price level")

        left_child = node.left
        right_child = node.right
        parent = node.parent

        was_best = self.best is node

        if left_child is None and right_child is None:
            # Node has no children
            if self.root is node:
                self.root = None
                self.best = None
            else:
                assert parent is not None
                if parent.left is node:
                    parent.left = None
                else:
                    parent.right = None

        elif (left_child is None and right_child is not None) or (left_child is not None and right_child is None):
            # Node has 1 child
            child = right_child if right_child is not None else left_child
            assert child is not None

            if self.root is node:
                self.root = child
                child.parent = None
            else:
                assert parent is not None

                if parent.left is node:
                    parent.left = child
                else:
                    parent.right = child

                child.parent = parent

        else:
            assert right_child is not None
            assert left_child is not None
            # Node has 2 children
            successor = self.get_minimum_node(right_child)

            if successor is right_child:
                # Successor is immediately right of node
                successor.left = left_child
                left_child.parent = successor
            else:
                # Successor is deeper in the BST
                assert successor.parent is not None
                successor.parent.left = successor.right

                if successor.right is not None:
                    successor.right.parent = successor.parent
                
                successor.left = left_child
                successor.right = right_child
                left_child.parent = successor
                right_child.parent = successor

            if self.root is node:
                self.root = successor
                successor.parent = None
            else:
                assert parent is not None

                successor.parent = parent
                if parent.left is node:
                    parent.left = successor
                else:
                    parent.right = successor

        node.parent = None
        node.left = None
        node.right = None

        if was_best:
            self.update_best_after_removal()
    
    def update_best_after_removal(self) -> None:
        """
        Updates the best bid/ask after PL removal
        """
        if self.root is None:
            self.best = None
        elif self.side is Side.BUY:
            self.best = self.get_maximum_node(self.root)
        elif self.side is Side.SELL:
            self.best = self.get_minimum_node(self.root)

    def add_order_node(self, order_node: OrderNode) -> None:
        """
        Adds a resting order to the BST
        """
        order = order_node.order

        if order.side != self.side:
            raise ValueError(
                f"Cannot add {order.side} order to {self.side} book side"
            )

        if order_node.tree_node is not None:
            raise ValueError("Order is already in a price level")

        if order.price is None:
            raise ValueError("Resting order must have a price")

        tree_node = self.get_price_level(order.price)

        if tree_node is None:
            tree_node = self.insert_price_level(order.price)

        tree_node.price_level.append_node(order_node)
        order_node.tree_node = tree_node

    def remove_order_node(self, order_node: OrderNode) -> None:
        """
        Removes a resting order from the BST
        """
        tree_node = order_node.tree_node

        if tree_node is None:
            raise ValueError("Order is not in a PL")
        
        price_level = tree_node.price_level
        price_level.remove_node(order_node)

        if price_level.is_empty():
            self.remove_price_level(tree_node)

    def get_price_levels_in_order(self) -> list[PriceLevel]:
        """
        Returns price levels in market order
        """
        price_levels: list[PriceLevel] = []
        stack: list[PriceTreeNode] = []
        curr = self.root

        reverse = self.side is Side.BUY

        while curr is not None or stack:
            while curr is not None:
                stack.append(curr)
                curr = curr.right if reverse else curr.left
            
            curr = stack.pop()
            price_levels.append(curr.price_level)

            curr = curr.left if reverse else curr.right
        
        return price_levels
