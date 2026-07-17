import unittest

from order_book_python.engine.book_side import BookSide
from order_book_python.engine.price_level import OrderNode
from order_book_python.engine.types.enums import Side

from .helpers import create_order


class TestBookSideInitialization(unittest.TestCase):
    def test_new_book_side_is_empty(self) -> None:
        book_side = BookSide(Side.BUY)

        self.assertEqual(book_side.side, Side.BUY)
        self.assertIsNone(book_side.root)
        self.assertIsNone(book_side.best)
        self.assertTrue(book_side.is_empty())
        self.assertIsNone(book_side.get_best_price())
        self.assertIsNone(book_side.get_best_level())
        self.assertIsNone(book_side.get_best_node())


class TestPriceLevelInsertion(unittest.TestCase):
    def test_first_level_becomes_root_and_best(self) -> None:
        book_side = BookSide(Side.BUY)

        node = book_side.insert_price_level(100)

        self.assertIs(book_side.root, node)
        self.assertIs(book_side.best, node)
        self.assertIsNone(node.parent)
        self.assertEqual(node.price_level.price, 100)

    def test_levels_are_inserted_into_bst(self) -> None:
        book_side = BookSide(Side.BUY)

        root = book_side.insert_price_level(100)
        left = book_side.insert_price_level(90)
        right = book_side.insert_price_level(110)

        self.assertIs(root.left, left)
        self.assertIs(root.right, right)

        self.assertIs(left.parent, root)
        self.assertIs(right.parent, root)

    def test_get_price_level_finds_existing_level(self) -> None:
        book_side = BookSide(Side.BUY)

        book_side.insert_price_level(100)
        expected = book_side.insert_price_level(90)
        book_side.insert_price_level(110)

        result = book_side.get_price_level(90)

        self.assertIs(result, expected)

    def test_get_price_level_returns_none_when_missing(self) -> None:
        book_side = BookSide(Side.BUY)

        book_side.insert_price_level(100)
        book_side.insert_price_level(90)

        self.assertIsNone(book_side.get_price_level(105))


class TestBestPrice(unittest.TestCase):
    def test_buy_side_best_is_highest_price(self) -> None:
        book_side = BookSide(Side.BUY)

        book_side.insert_price_level(100)
        book_side.insert_price_level(90)
        highest = book_side.insert_price_level(110)

        self.assertIs(book_side.best, highest)
        self.assertEqual(book_side.get_best_price(), 110)
        self.assertIs(book_side.get_best_level(), highest.price_level)

    def test_sell_side_best_is_lowest_price(self) -> None:
        book_side = BookSide(Side.SELL)

        book_side.insert_price_level(100)
        lowest = book_side.insert_price_level(90)
        book_side.insert_price_level(110)

        self.assertIs(book_side.best, lowest)
        self.assertEqual(book_side.get_best_price(), 90)
        self.assertIs(book_side.get_best_level(), lowest.price_level)

    def test_get_minimum_and_maximum_nodes(self) -> None:
        book_side = BookSide(Side.BUY)

        root = book_side.insert_price_level(100)
        minimum = book_side.insert_price_level(80)
        book_side.insert_price_level(90)
        book_side.insert_price_level(110)
        maximum = book_side.insert_price_level(120)

        self.assertIs(book_side.get_minimum_node(root), minimum)
        self.assertIs(book_side.get_maximum_node(root), maximum)


class TestPriceLevelRemoval(unittest.TestCase):
    def test_remove_only_root(self) -> None:
        book_side = BookSide(Side.BUY)
        root = book_side.insert_price_level(100)

        book_side.remove_price_level(root)

        self.assertIsNone(book_side.root)
        self.assertIsNone(book_side.best)
        self.assertTrue(book_side.is_empty())

    def test_remove_leaf(self) -> None:
        book_side = BookSide(Side.BUY)

        root = book_side.insert_price_level(100)
        leaf = book_side.insert_price_level(90)
        best = book_side.insert_price_level(110)

        book_side.remove_price_level(leaf)

        self.assertIsNone(root.left)
        self.assertIs(root.right, best)
        self.assertIs(book_side.best, best)

    def test_remove_root_with_one_child(self) -> None:
        book_side = BookSide(Side.BUY)

        root = book_side.insert_price_level(100)
        child = book_side.insert_price_level(90)

        book_side.remove_price_level(root)

        self.assertIs(book_side.root, child)
        self.assertIsNone(child.parent)
        self.assertIs(book_side.best, child)

    def test_remove_non_root_with_one_child(self) -> None:
        book_side = BookSide(Side.BUY)

        root = book_side.insert_price_level(100)
        node = book_side.insert_price_level(90)
        child = book_side.insert_price_level(95)

        book_side.remove_price_level(node)

        self.assertIs(root.left, child)
        self.assertIs(child.parent, root)

    def test_remove_root_with_two_children(self) -> None:
        book_side = BookSide(Side.BUY)

        root = book_side.insert_price_level(100)
        left = book_side.insert_price_level(90)
        successor = book_side.insert_price_level(110)

        book_side.remove_price_level(root)

        self.assertIs(book_side.root, successor)
        self.assertIsNone(successor.parent)
        self.assertIs(successor.left, left)
        self.assertIs(left.parent, successor)
        self.assertIs(book_side.best, successor)

    def test_remove_node_with_deeper_successor(self) -> None:
        book_side = BookSide(Side.BUY)

        root = book_side.insert_price_level(100)
        left = book_side.insert_price_level(80)
        right = book_side.insert_price_level(150)
        successor = book_side.insert_price_level(120)
        successor_child = book_side.insert_price_level(130)

        book_side.remove_price_level(root)

        self.assertIs(book_side.root, successor)
        self.assertIsNone(successor.parent)

        self.assertIs(successor.left, left)
        self.assertIs(left.parent, successor)

        self.assertIs(successor.right, right)
        self.assertIs(right.parent, successor)

        self.assertIs(right.left, successor_child)
        self.assertIs(successor_child.parent, right)

        self.assertEqual(book_side.get_best_price(), 150)

    def test_removing_buy_best_updates_best_pointer(self) -> None:
        book_side = BookSide(Side.BUY)

        book_side.insert_price_level(90)
        expected_best = book_side.insert_price_level(100)
        old_best = book_side.insert_price_level(110)

        book_side.remove_price_level(old_best)

        self.assertIs(book_side.best, expected_best)
        self.assertEqual(book_side.get_best_price(), 100)

    def test_removing_sell_best_updates_best_pointer(self) -> None:
        book_side = BookSide(Side.SELL)

        old_best = book_side.insert_price_level(90)
        expected_best = book_side.insert_price_level(100)
        book_side.insert_price_level(110)

        book_side.remove_price_level(old_best)

        self.assertIs(book_side.best, expected_best)
        self.assertEqual(book_side.get_best_price(), 100)


class TestOrderNodeManagement(unittest.TestCase):
    def test_add_order_creates_price_level(self) -> None:
        book_side = BookSide(Side.BUY)

        order_node = OrderNode(
            create_order(
                order_id=1,
                side=Side.BUY,
                price=100,
                size=10
            )
        )

        book_side.add_order_node(order_node)

        tree_node = book_side.get_price_level(100)

        self.assertIsNotNone(tree_node)
        assert tree_node is not None

        self.assertIs(order_node.tree_node, tree_node)
        self.assertIs(tree_node.price_level.head, order_node)
        self.assertIs(tree_node.price_level.tail, order_node)
        self.assertEqual(tree_node.price_level.total_size, 10)
        self.assertEqual(tree_node.price_level.order_count, 1)

    def test_orders_at_same_price_use_fifo_queue(self) -> None:
        book_side = BookSide(Side.BUY)

        first = OrderNode(create_order(1, Side.BUY, 100, 10))
        second = OrderNode(create_order(2, Side.BUY, 100, 20))

        book_side.add_order_node(first)
        book_side.add_order_node(second)

        tree_node = book_side.get_price_level(100)

        assert tree_node is not None
        level = tree_node.price_level

        self.assertIs(level.head, first)
        self.assertIs(level.tail, second)
        self.assertIs(first.next, second)
        self.assertIs(second.prev, first)
        self.assertEqual(level.total_size, 30)
        self.assertEqual(level.order_count, 2)

    def test_remove_order_keeps_non_empty_price_level(self) -> None:
        book_side = BookSide(Side.BUY)

        first = OrderNode(create_order(1, Side.BUY, 100, 10))
        second = OrderNode(create_order(2, Side.BUY, 100, 20))

        book_side.add_order_node(first)
        book_side.add_order_node(second)

        book_side.remove_order_node(first)

        tree_node = book_side.get_price_level(100)

        self.assertIsNotNone(tree_node)
        assert tree_node is not None

        self.assertIs(tree_node.price_level.head, second)
        self.assertEqual(tree_node.price_level.total_size, 20)
        self.assertEqual(tree_node.price_level.order_count, 1)
        self.assertIsNone(first.tree_node)

    def test_remove_last_order_removes_price_level(self) -> None:
        book_side = BookSide(Side.BUY)

        order_node = OrderNode(create_order(1, Side.BUY, 100, 10))

        book_side.add_order_node(order_node)
        book_side.remove_order_node(order_node)

        self.assertIsNone(book_side.get_price_level(100))
        self.assertTrue(book_side.is_empty())
        self.assertIsNone(book_side.best)


class TestPriceLevelOrdering(unittest.TestCase):
    def test_buy_levels_are_best_to_worst(self) -> None:
        book_side = BookSide(Side.BUY)

        book_side.insert_price_level(100)
        book_side.insert_price_level(98)
        book_side.insert_price_level(102)
        book_side.insert_price_level(99)

        prices = [level.price for level in book_side.get_price_levels_in_order()]

        self.assertEqual(prices, [102, 100, 99, 98])

    def test_sell_levels_are_best_to_worst(self) -> None:
        book_side = BookSide(Side.SELL)

        book_side.insert_price_level(100)
        book_side.insert_price_level(98)
        book_side.insert_price_level(102)
        book_side.insert_price_level(99)

        prices = [level.price for level in book_side.get_price_levels_in_order()]

        self.assertEqual(prices, [98, 99, 100, 102])


if __name__ == "__main__":
    unittest.main()
