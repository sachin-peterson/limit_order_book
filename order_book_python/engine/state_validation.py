from __future__ import annotations
from typing import TYPE_CHECKING

from .book_side import BookSide, PriceTreeNode
from .price_level import OrderNode
from .types.enums import EventType, OrderStatus, OrderType, Side, TimeInForce
from .types.instruments import Instrument
if TYPE_CHECKING: from .matching_engine import OrderBook


def validate_state(order_book: OrderBook) -> None:
    """
    Validates the internal state of the order book
    """
    discovered_orders: dict[int, OrderNode] = {}

    # Validate the buy side
    validate_book_side(
        book_side=order_book.bids,
        expected_side=Side.BUY,
        instrument=order_book.instrument,
        discovered_orders=discovered_orders
    )

    # Validate the sell side
    validate_book_side(
        book_side=order_book.asks,
        expected_side=Side.SELL,
        instrument=order_book.instrument,
        discovered_orders=discovered_orders
    )

    # Compare the book w/ the order index
    discovered_ids = set(discovered_orders)
    indexed_ids = set(order_book.order_index)

    if discovered_ids != indexed_ids:
        missing_from_index = discovered_ids - indexed_ids
        missing_from_book = indexed_ids - discovered_ids

        raise AssertionError(
            "Order index does not match the book: "
            f"missing from index={missing_from_index}, "
            f"missing from book={missing_from_book}"
        )

    # Check each index entry
    for order_id, indexed_node in order_book.order_index.items():
        if indexed_node.order.order_id != order_id:
            raise AssertionError(
                f"Order index key {order_id} points to order "
                f"{indexed_node.order.order_id}"
            )

        if discovered_orders[order_id] is not indexed_node:
            raise AssertionError(
                f"Order index points to the wrong node for order {order_id}"
            )

    # Check for a crossed book
    best_bid = order_book.get_best_bid_price()
    best_ask = order_book.get_best_ask_price()

    if (
        best_bid is not None
        and best_ask is not None
        and best_bid >= best_ask
    ):
        raise AssertionError(
            f"Crossed book: best bid {best_bid}, best ask {best_ask}"
        )

    # Validate identifiers
    validate_order_ids(order_book)
    validate_trade_ids(order_book)
    validate_event_sequences(order_book)

def validate_book_side(
    book_side: BookSide,
    expected_side: Side,
    instrument: Instrument,
    discovered_orders: dict[int, OrderNode]
) -> None:
    """
    Validates the state of one side of the book
    """
    # Validate an empty tree
    if book_side.side is not expected_side:
        raise AssertionError(
            f"Expected {expected_side.value} book, "
            f"found {book_side.side.value}"
        )

    # Validate a non-empty tree
    if book_side.root is None:
        if book_side.best is not None:
            raise AssertionError(
                f"Empty {expected_side.value} book has a best pointer"
            )

        return

    if book_side.best is None:
        raise AssertionError(
            f"Non-empty {expected_side.value} book has no best pointer"
        )

    if book_side.root.parent is not None:
        raise AssertionError(
            f"{expected_side.value} root has a parent"
        )

    # Track visited tree nodes
    seen_tree_nodes: set[int] = set()

    # Recursively validate the tree
    validate_tree_node(
        node=book_side.root,
        expected_parent=None,
        lower_bound=None,
        upper_bound=None,
        expected_side=expected_side,
        instrument=instrument,
        discovered_orders=discovered_orders,
        seen_tree_nodes=seen_tree_nodes
    )

    # Check expected best nodes
    if expected_side is Side.BUY:
        expected_best = book_side.get_maximum_node(book_side.root)
    else:
        expected_best = book_side.get_minimum_node(book_side.root)

    if book_side.best is not expected_best:
        raise AssertionError(
            f"Incorrect best pointer on {expected_side.value} side"
        )

def validate_tree_node(
    node: PriceTreeNode,
    expected_parent: PriceTreeNode | None,
    lower_bound: int | None,
    upper_bound: int | None,
    expected_side: Side,
    instrument: Instrument,
    discovered_orders: dict[int, OrderNode],
    seen_tree_nodes: set[int]
) -> None:
    """
    Validates one price tree node, then recursively validates its children
    """
    node_identity = id(node)

    # Check for cycles/repeated nodes
    if node_identity in seen_tree_nodes:
        raise AssertionError(
            "Cycle or repeated node detected in price tree"
        )

    seen_tree_nodes.add(node_identity)

    # Verify the parent pointer
    if node.parent is not expected_parent:
        raise AssertionError(
            f"Incorrect parent pointer at price {node.price_level.price}"
        )

    price = node.price_level.price

    # Validate the BST boundaries
    if lower_bound is not None and price <= lower_bound:
        raise AssertionError(
            f"BST violation: {price} is not greater than {lower_bound}"
        )

    if upper_bound is not None and price >= upper_bound:
        raise AssertionError(
            f"BST violation: {price} is not less than {upper_bound}"
        )

    # Validate the price itself
    if price <= 0:
        raise AssertionError(f"Non-positive price level: {price}")

    if price % instrument.tick_size != 0:
        raise AssertionError(
            f"Price level {price} is not a multiple of tick size"
        )

    # Validate the FIFO queue at this price
    validate_price_level(
        tree_node=node,
        expected_side=expected_side,
        instrument=instrument,
        discovered_orders=discovered_orders
    )

    # Recurse into left child
    if node.left is not None:
        validate_tree_node(
            node=node.left,
            expected_parent=node,
            lower_bound=lower_bound,
            upper_bound=price,
            expected_side=expected_side,
            instrument=instrument,
            discovered_orders=discovered_orders,
            seen_tree_nodes=seen_tree_nodes
        )

    # Recurse into right child
    if node.right is not None:
        validate_tree_node(
            node=node.right,
            expected_parent=node,
            lower_bound=price,
            upper_bound=upper_bound,
            expected_side=expected_side,
            instrument=instrument,
            discovered_orders=discovered_orders,
            seen_tree_nodes=seen_tree_nodes
        )

def validate_price_level(
    tree_node: PriceTreeNode,
    expected_side: Side,
    instrument: Instrument,
    discovered_orders: dict[int, OrderNode]
) -> None:
    """
    Validates the FIFO doubly linked list at one price level
    """
    price_level = tree_node.price_level

    # Validate the level price
    if price_level.order_count <= 0:
        raise AssertionError(
            f"Empty price level {price_level.price} remains in the tree"
        )

    # Validate the level size
    if price_level.total_size <= 0:
        raise AssertionError(
            f"Price level {price_level.price} has non-positive size"
        )

    # Check queue endpoints
    if price_level.head is None or price_level.tail is None:
        raise AssertionError(
            f"Price level {price_level.price} is missing head or tail"
        )

    if price_level.head.prev is not None:
        raise AssertionError(
            f"Head at price {price_level.price} has a prev pointer"
        )

    if price_level.tail.next is not None:
        raise AssertionError(
            f"Tail at price {price_level.price} has a next pointer"
        )

    calculated_size = 0
    calculated_count = 0
    seen_order_nodes: set[int] = set()

    current = price_level.head
    previous: OrderNode | None = None

    # Traverse the DLL
    while current is not None:
        current_identity = id(current)

        # Check for cycles
        if current_identity in seen_order_nodes:
            raise AssertionError(
                f"Cycle detected at price {price_level.price}"
            )

        seen_order_nodes.add(current_identity)

        # Check pointers
        if current.prev is not previous:
            raise AssertionError(
                f"Incorrect prev pointer at price {price_level.price}"
            )

        if current.tree_node is not tree_node:
            raise AssertionError(
                f"Order {current.order.order_id} has wrong tree node"
            )

        order = current.order

        # Check for duplicates
        if order.order_id in discovered_orders:
            raise AssertionError(
                f"Duplicate active order ID {order.order_id}"
            )

        # Validate order parameters
        if order.side is not expected_side:
            raise AssertionError(
                f"Order {order.order_id} is on the wrong side"
            )

        if order.status is not OrderStatus.ACTIVE:
            raise AssertionError(
                f"Resting order {order.order_id} is not active"
            )

        if order.price != price_level.price:
            raise AssertionError(
                f"Order {order.order_id} has price {order.price}, "
                f"but is stored at {price_level.price}"
            )

        if order.size <= 0:
            raise AssertionError(
                f"Order {order.order_id} has non-positive size"
            )

        if order.size % instrument.lot_size != 0:
            raise AssertionError(
                f"Order {order.order_id} size violates lot size"
            )

        # Only LIMIT orders can rest in the book
        if order.order_type is not OrderType.LIMIT:
            raise AssertionError(
                f"Non-limit order {order.order_id} is resting"
            )

        if order.time_in_force is not TimeInForce.GTC:
            raise AssertionError(
                f"Non-GTC order {order.order_id} is resting"
            )

        discovered_orders[order.order_id] = current

        calculated_size += order.size
        calculated_count += 1

        previous = current
        current = current.next

    # Verify the final node
    if previous is not price_level.tail:
        raise AssertionError(
            f"Incorrect tail pointer at price {price_level.price}"
        )

    # Compare calculated size
    if calculated_size != price_level.total_size:
        raise AssertionError(
            f"Incorrect total size at price {price_level.price}: "
            f"expected {calculated_size}, "
            f"found {price_level.total_size}"
        )

    # Compare calculated count
    if calculated_count != price_level.order_count:
        raise AssertionError(
            f"Incorrect order count at price {price_level.price}: "
            f"expected {calculated_count}, "
            f"found {price_level.order_count}"
        )

    current = price_level.tail
    next_node: OrderNode | None = None
    reverse_count = 0

    # Traverse backwards
    while current is not None:
        if current.next is not next_node:
            raise AssertionError(
                f"Incorrect next pointer at price {price_level.price}"
            )

        reverse_count += 1
        next_node = current
        current = current.prev

    # Verify the final node
    if next_node is not price_level.head:
        raise AssertionError(
            f"Backward traversal does not reach the head "
            f"at price {price_level.price}"
        )

    # Verify the count again
    if reverse_count != calculated_count:
        raise AssertionError(
            f"Forward and backward queue counts differ "
            f"at price {price_level.price}"
        )
    
def validate_order_ids(order_book: OrderBook) -> None:
    """
    Validates IDs assigned to accepted orders
    """
    if order_book.next_order_id <= 0:
        raise AssertionError("Next order ID must be positive")

    # Collect order IDs
    order_ids: list[int] = []
    for event in order_book.events:
        if event.event_type is not EventType.ORDER_ACCEPTED:
            continue

        order_id = event.details.get("order_id")

        if not isinstance(order_id, int):
            raise AssertionError(
                "Accepted-order event is missing an order ID"
            )

        order_ids.append(order_id)

    # Check for duplicates
    if len(order_ids) != len(set(order_ids)):
        raise AssertionError("Duplicate order ID detected")

    # Verify that the generator is ahead
    if order_ids and order_book.next_order_id <= max(order_ids):
        raise AssertionError(
            "Next order ID must exceed all issued order IDs"
        )

def validate_trade_ids(order_book: OrderBook) -> None:
    """
    Validates IDs assigned to executed trades
    """
    if order_book.next_trade_id <= 0:
        raise AssertionError("Next trade ID must be positive")

    # Collect trade IDs
    trade_ids: list[int] = []
    for event in order_book.events:
        if event.event_type is not EventType.TRADE_EXECUTED:
            continue

        trade_id = event.details.get("trade_id")

        if not isinstance(trade_id, int):
            raise AssertionError(
                "Trade event is missing a trade ID"
            )

        trade_ids.append(trade_id)

    # Check for duplicates
    if len(trade_ids) != len(set(trade_ids)):
        raise AssertionError("Duplicate trade ID detected")

    # Verify that the generator is ahead
    if trade_ids and order_book.next_trade_id <= max(trade_ids):
        raise AssertionError(
            "Next trade ID must exceed all issued trade IDs"
        )

def validate_event_sequences(order_book: OrderBook) -> None:
    """
    Validates the sequence of event numbers
    """
    if order_book.event_sequence <= 0:
        raise AssertionError("Event sequence must be positive")

    # Construct the expected sequence
    expected_sequences = list(range(1, order_book.event_sequence))

    # Retrieve the actual sequence
    actual_sequences = [event.sequence for event in order_book.events]

    # Compare expected vs actual
    if actual_sequences != expected_sequences:
        raise AssertionError(
            "Event sequences must be contiguous and ordered"
        )
