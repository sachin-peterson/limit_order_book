import unittest

from order_book_python.engine.book_side import PriceTreeNode
from order_book_python.engine.price_level import OrderNode, PriceLevel
from order_book_python.engine.types.enums import Side

from .helpers import create_order


class TestPriceLevelInitialization(unittest.TestCase):
    def test_new_price_level_is_empty(self) -> None:
        level = PriceLevel(100)

        self.assertEqual(level.price, 100)
        self.assertIsNone(level.head)
        self.assertIsNone(level.tail)
        self.assertEqual(level.total_size, 0)
        self.assertEqual(level.order_count, 0)
        self.assertTrue(level.is_empty())

    def test_rejects_non_positive_price(self) -> None:
        with self.assertRaises(ValueError):
            PriceLevel(0)

        with self.assertRaises(ValueError):
            PriceLevel(-1)


class TestPriceLevelAppend(unittest.TestCase):
    def setUp(self) -> None:
        self.level = PriceLevel(100)
        self.tree_node = PriceTreeNode(self.level)

    def append_node(self, node: OrderNode) -> None:
        self.level.append_node(node)
        node.tree_node = self.tree_node

    def test_append_first_node(self) -> None:
        node = OrderNode(
            create_order(
                order_id=1,
                side=Side.BUY,
                price=100,
                size=10
            )
        )

        self.append_node(node)

        self.assertIs(self.level.head, node)
        self.assertIs(self.level.tail, node)
        self.assertIsNone(node.prev)
        self.assertIsNone(node.next)
        self.assertEqual(self.level.total_size, 10)
        self.assertEqual(self.level.order_count, 1)
        self.assertFalse(self.level.is_empty())

    def test_append_multiple_nodes_uses_fifo_order(self) -> None:
        first = OrderNode(create_order(1, Side.BUY, 100, 10))
        second = OrderNode(create_order(2, Side.BUY, 100, 20))
        third = OrderNode(create_order(3, Side.BUY, 100, 30))

        self.append_node(first)
        self.append_node(second)
        self.append_node(third)

        self.assertIs(self.level.head, first)
        self.assertIs(self.level.tail, third)

        self.assertIsNone(first.prev)
        self.assertIs(first.next, second)

        self.assertIs(second.prev, first)
        self.assertIs(second.next, third)

        self.assertIs(third.prev, second)
        self.assertIsNone(third.next)

        self.assertEqual(self.level.total_size, 60)
        self.assertEqual(self.level.order_count, 3)

    def test_rejects_node_already_in_level(self) -> None:
        node = OrderNode(create_order(1, Side.BUY, 100))

        self.append_node(node)

        with self.assertRaises(ValueError):
            self.level.append_node(node)


class TestPriceLevelRemoval(unittest.TestCase):
    def setUp(self) -> None:
        self.level = PriceLevel(100)
        self.tree_node = PriceTreeNode(self.level)

    def append_node(self, node: OrderNode) -> None:
        self.level.append_node(node)
        node.tree_node = self.tree_node

    def test_remove_only_node(self) -> None:
        node = OrderNode(create_order(1, Side.BUY, 100, 10))
        self.append_node(node)

        self.level.remove_node(node)

        self.assertIsNone(self.level.head)
        self.assertIsNone(self.level.tail)
        self.assertEqual(self.level.total_size, 0)
        self.assertEqual(self.level.order_count, 0)
        self.assertTrue(self.level.is_empty())

        self.assertIsNone(node.prev)
        self.assertIsNone(node.next)
        self.assertIsNone(node.tree_node)

    def test_remove_head(self) -> None:
        first = OrderNode(create_order(1, Side.BUY, 100, 10))
        second = OrderNode(create_order(2, Side.BUY, 100, 20))
        third = OrderNode(create_order(3, Side.BUY, 100, 30))

        self.append_node(first)
        self.append_node(second)
        self.append_node(third)

        self.level.remove_node(first)

        self.assertIs(self.level.head, second)
        self.assertIs(self.level.tail, third)
        self.assertIsNone(second.prev)
        self.assertIs(second.next, third)
        self.assertEqual(self.level.total_size, 50)
        self.assertEqual(self.level.order_count, 2)

        self.assertIsNone(first.prev)
        self.assertIsNone(first.next)
        self.assertIsNone(first.tree_node)

    def test_remove_tail(self) -> None:
        first = OrderNode(create_order(1, Side.BUY, 100, 10))
        second = OrderNode(create_order(2, Side.BUY, 100, 20))
        third = OrderNode(create_order(3, Side.BUY, 100, 30))

        self.append_node(first)
        self.append_node(second)
        self.append_node(third)

        self.level.remove_node(third)

        self.assertIs(self.level.head, first)
        self.assertIs(self.level.tail, second)
        self.assertIsNone(second.next)
        self.assertEqual(self.level.total_size, 30)
        self.assertEqual(self.level.order_count, 2)

        self.assertIsNone(third.prev)
        self.assertIsNone(third.next)
        self.assertIsNone(third.tree_node)

    def test_remove_middle_node(self) -> None:
        first = OrderNode(create_order(1, Side.BUY, 100, 10))
        second = OrderNode(create_order(2, Side.BUY, 100, 20))
        third = OrderNode(create_order(3, Side.BUY, 100, 30))

        self.append_node(first)
        self.append_node(second)
        self.append_node(third)

        self.level.remove_node(second)

        self.assertIs(self.level.head, first)
        self.assertIs(self.level.tail, third)
        self.assertIs(first.next, third)
        self.assertIs(third.prev, first)
        self.assertEqual(self.level.total_size, 40)
        self.assertEqual(self.level.order_count, 2)

        self.assertIsNone(second.prev)
        self.assertIsNone(second.next)
        self.assertIsNone(second.tree_node)

    def test_rejects_node_from_another_level(self) -> None:
        other_level = PriceLevel(101)
        other_tree_node = PriceTreeNode(other_level)

        node = OrderNode(create_order(1, Side.BUY, 101))
        other_level.append_node(node)
        node.tree_node = other_tree_node

        with self.assertRaises(ValueError):
            self.level.remove_node(node)


class TestPriceLevelUpdates(unittest.TestCase):
    def test_update_node_size_adjusts_total_size(self) -> None:
        level = PriceLevel(100)
        tree_node = PriceTreeNode(level)

        node = OrderNode(
            create_order(
                order_id=1,
                side=Side.BUY,
                price=100,
                size=10
            )
        )

        level.append_node(node)
        node.tree_node = tree_node

        level.update_node_size(node, 25)

        self.assertEqual(node.order.size, 25)
        self.assertEqual(level.total_size, 25)
        self.assertEqual(level.order_count, 1)

    def test_getters_return_queue_state(self) -> None:
        level = PriceLevel(100)
        tree_node = PriceTreeNode(level)

        first = OrderNode(create_order(1, Side.BUY, 100, 10))
        second = OrderNode(create_order(2, Side.BUY, 100, 20))

        level.append_node(first)
        first.tree_node = tree_node

        level.append_node(second)
        second.tree_node = tree_node

        self.assertIs(level.get_first(), first)
        self.assertIs(level.get_last(), second)
        self.assertEqual(level.get_total_size(), 30)
        self.assertEqual(level.get_order_count(), 2)


if __name__ == "__main__":
    unittest.main()
    