import unittest

from order_book_python.engine.types.enums import EventType, OrderStatus, Side, TimeInForce
from order_book_python.engine.types.requests import CancelOrderRequest, ModifyOrderRequest

from .helpers import create_order_book, limit_request, market_request


class TestOrderSubmission(unittest.TestCase):
    def setUp(self) -> None:
        self.book = create_order_book()

    def test_new_book_is_empty(self) -> None:
        self.assertTrue(self.book.is_empty())
        self.assertEqual(self.book.order_index, {})
        self.assertEqual(self.book.events, [])
        self.assertIsNone(self.book.get_best_bid_price())
        self.assertIsNone(self.book.get_best_ask_price())

    def test_limit_gtc_order_rests_on_buy_side(self) -> None:
        order = self.book.submit_order(
            limit_request(
                request_id=1,
                client_id=10,
                side=Side.BUY,
                price=100,
                size=10
            )
        )

        self.assertEqual(order.status, OrderStatus.ACTIVE)
        self.assertEqual(order.size, 10)

        self.assertTrue(self.book.has_order(order.order_id))
        self.assertIs(self.book.get_order(order.order_id), order)

        self.assertEqual(self.book.get_best_bid_price(), 100)
        self.assertIsNone(self.book.get_best_ask_price())
        self.assertEqual(self.book.get_depth_at_price(Side.BUY, 100), 10)

        self.assertEqual(
            [event.event_type for event in self.book.events],
            [EventType.ORDER_ACCEPTED, EventType.ORDER_RESTED]
        )

    def test_limit_gtc_order_rests_on_sell_side(self) -> None:
        order = self.book.submit_order(
            limit_request(
                request_id=1,
                client_id=10,
                side=Side.SELL,
                price=105,
                size=20
            )
        )

        self.assertEqual(order.status, OrderStatus.ACTIVE)
        self.assertTrue(self.book.has_order(order.order_id))
        self.assertEqual(self.book.get_best_ask_price(), 105)
        self.assertEqual(self.book.get_depth_at_price(Side.SELL, 105), 20)

    def test_non_crossing_orders_create_spread(self) -> None:
        self.book.submit_order(
            limit_request(1, 10, Side.BUY, 100, 10)
        )
        self.book.submit_order(
            limit_request(2, 20, Side.SELL, 105, 20)
        )

        self.assertEqual(self.book.get_best_bid_price(), 100)
        self.assertEqual(self.book.get_best_ask_price(), 105)
        self.assertEqual(self.book.get_bid_ask_spread(), 5)
        self.assertEqual(self.book.get_mid_price(), 102.5)

    def test_rejected_order_emits_rejection_event(self) -> None:
        book = create_order_book(
            tick_size=5,
            lot_size=10
        )

        request = limit_request(
            request_id=1,
            client_id=10,
            side=Side.BUY,
            price=103,
            size=20
        )

        with self.assertRaises(ValueError):
            book.submit_order(request)

        self.assertEqual(len(book.events), 1)
        self.assertEqual(book.events[0].event_type, EventType.ORDER_REJECTED)
        self.assertEqual(book.events[0].details["request_id"], request.request_id)
        self.assertEqual(book.order_index, {})


class TestLimitOrderMatching(unittest.TestCase):
    def setUp(self) -> None:
        self.book = create_order_book()

    def test_crossing_buy_fills_sell_order(self) -> None:
        sell_order = self.book.submit_order(
            limit_request(1, 10, Side.SELL, 100, 10)
        )

        buy_order = self.book.submit_order(
            limit_request(2, 20, Side.BUY, 100, 10)
        )

        self.assertEqual(sell_order.status, OrderStatus.FILLED)
        self.assertEqual(buy_order.status, OrderStatus.FILLED)

        self.assertEqual(sell_order.size, 0)
        self.assertEqual(buy_order.size, 0)

        self.assertFalse(self.book.has_order(sell_order.order_id))
        self.assertFalse(self.book.has_order(buy_order.order_id))
        self.assertTrue(self.book.is_empty())

    def test_crossing_sell_fills_buy_order(self) -> None:
        buy_order = self.book.submit_order(
            limit_request(1, 10, Side.BUY, 100, 10)
        )

        sell_order = self.book.submit_order(
            limit_request(2, 20, Side.SELL, 100, 10)
        )

        self.assertEqual(buy_order.status, OrderStatus.FILLED)
        self.assertEqual(sell_order.status, OrderStatus.FILLED)
        self.assertTrue(self.book.is_empty())

    def test_trade_executes_at_maker_price(self) -> None:
        self.book.submit_order(
            limit_request(1, 10, Side.SELL, 100, 10)
        )

        self.book.submit_order(
            limit_request(2, 20, Side.BUY, 105, 10)
        )

        trade_events = [
            event
            for event in self.book.events
            if event.event_type is EventType.TRADE_EXECUTED
        ]

        self.assertEqual(len(trade_events), 1)
        self.assertEqual(trade_events[0].details["trade_price"], 100)
        self.assertEqual(trade_events[0].details["trade_size"], 10)

    def test_non_crossing_buy_order_does_not_trade(self) -> None:
        sell_order = self.book.submit_order(
            limit_request(1, 10, Side.SELL, 105, 10)
        )

        buy_order = self.book.submit_order(
            limit_request(2, 20, Side.BUY, 100, 10)
        )

        self.assertEqual(sell_order.status, OrderStatus.ACTIVE)
        self.assertEqual(buy_order.status, OrderStatus.ACTIVE)

        self.assertEqual(self.book.get_best_bid_price(), 100)
        self.assertEqual(self.book.get_best_ask_price(), 105)

        trade_events = [
            event
            for event in self.book.events
            if event.event_type is EventType.TRADE_EXECUTED
        ]

        self.assertEqual(trade_events, [])

    def test_partial_maker_fill_leaves_remainder_resting(self) -> None:
        maker = self.book.submit_order(
            limit_request(1, 10, Side.SELL, 100, 10)
        )

        taker = self.book.submit_order(
            limit_request(2, 20, Side.BUY, 100, 4)
        )

        self.assertEqual(maker.status, OrderStatus.ACTIVE)
        self.assertEqual(maker.size, 6)

        self.assertEqual(taker.status, OrderStatus.FILLED)
        self.assertEqual(taker.size, 0)

        self.assertTrue(self.book.has_order(maker.order_id))
        self.assertFalse(self.book.has_order(taker.order_id))

        self.assertEqual(self.book.get_depth_at_price(Side.SELL, 100), 6)

    def test_partial_gtc_taker_rests_remaining_size(self) -> None:
        maker = self.book.submit_order(
            limit_request(1, 10, Side.SELL, 100, 5)
        )

        taker = self.book.submit_order(
            limit_request(2, 20, Side.BUY, 100, 10)
        )

        self.assertEqual(maker.status, OrderStatus.FILLED)
        self.assertEqual(maker.size, 0)

        self.assertEqual(taker.status, OrderStatus.ACTIVE)
        self.assertEqual(taker.size, 5)

        self.assertTrue(self.book.has_order(taker.order_id))
        self.assertEqual(self.book.get_best_bid_price(), 100)
        self.assertIsNone(self.book.get_best_ask_price())

    def test_order_matches_multiple_price_levels(self) -> None:
        first = self.book.submit_order(
            limit_request(1, 10, Side.SELL, 100, 5)
        )
        second = self.book.submit_order(
            limit_request(2, 20, Side.SELL, 101, 5)
        )

        taker = self.book.submit_order(
            limit_request(3, 30, Side.BUY, 101, 10)
        )

        self.assertEqual(first.status, OrderStatus.FILLED)
        self.assertEqual(second.status, OrderStatus.FILLED)
        self.assertEqual(taker.status, OrderStatus.FILLED)
        self.assertTrue(self.book.is_empty())

        trade_prices = [
            event.details["trade_price"]
            for event in self.book.events
            if event.event_type is EventType.TRADE_EXECUTED
        ]

        self.assertEqual(trade_prices, [100, 101])

    def test_limit_order_does_not_trade_beyond_limit_price(self) -> None:
        first = self.book.submit_order(
            limit_request(1, 10, Side.SELL, 100, 5)
        )
        second = self.book.submit_order(
            limit_request(2, 20, Side.SELL, 101, 5)
        )

        taker = self.book.submit_order(
            limit_request(3, 30, Side.BUY, 100, 10)
        )

        self.assertEqual(first.status, OrderStatus.FILLED)
        self.assertEqual(second.status, OrderStatus.ACTIVE)

        self.assertEqual(taker.status, OrderStatus.ACTIVE)
        self.assertEqual(taker.size, 5)

        self.assertEqual(self.book.get_best_bid_price(), 100)
        self.assertEqual(self.book.get_best_ask_price(), 101)


class TestFifoPriority(unittest.TestCase):
    def setUp(self) -> None:
        self.book = create_order_book()

    def test_first_order_at_price_fills_first(self) -> None:
        first = self.book.submit_order(
            limit_request(1, 10, Side.SELL, 100, 5)
        )
        second = self.book.submit_order(
            limit_request(2, 20, Side.SELL, 100, 5)
        )

        self.book.submit_order(
            market_request(3, 30, Side.BUY, 5)
        )

        self.assertEqual(first.status, OrderStatus.FILLED)
        self.assertEqual(second.status, OrderStatus.ACTIVE)

        remaining_orders = self.book.get_orders_at_price(Side.SELL, 100)

        self.assertEqual(remaining_orders, [second])

    def test_fifo_order_across_partial_fill(self) -> None:
        first = self.book.submit_order(
            limit_request(1, 10, Side.SELL, 100, 5)
        )
        second = self.book.submit_order(
            limit_request(2, 20, Side.SELL, 100, 5)
        )

        self.book.submit_order(
            market_request(3, 30, Side.BUY, 7)
        )

        self.assertEqual(first.status, OrderStatus.FILLED)
        self.assertEqual(first.size, 0)

        self.assertEqual(second.status, OrderStatus.ACTIVE)
        self.assertEqual(second.size, 3)

        remaining_orders = self.book.get_orders_at_price(Side.SELL, 100)

        self.assertEqual(remaining_orders, [second])


class TestMarketOrders(unittest.TestCase):
    def setUp(self) -> None:
        self.book = create_order_book()

    def test_market_order_consumes_best_prices_first(self) -> None:
        self.book.submit_order(
            limit_request(1, 10, Side.SELL, 101, 5)
        )
        self.book.submit_order(
            limit_request(2, 20, Side.SELL, 100, 5)
        )

        order = self.book.submit_order(
            market_request(3, 30, Side.BUY, 10)
        )

        self.assertEqual(order.status, OrderStatus.FILLED)

        trade_prices = [
            event.details["trade_price"]
            for event in self.book.events
            if event.event_type is EventType.TRADE_EXECUTED
        ]

        self.assertEqual(trade_prices, [100, 101])

    def test_market_order_with_no_liquidity_is_cancelled(self) -> None:
        order = self.book.submit_order(
            market_request(1, 10, Side.BUY, 10)
        )

        self.assertEqual(order.status, OrderStatus.CANCELLED)
        self.assertEqual(order.size, 0)
        self.assertFalse(self.book.has_order(order.order_id))

        self.assertEqual(self.book.events[-1].event_type, EventType.ORDER_REMAINDER_CANCELLED)
        self.assertEqual(self.book.events[-1].details["cancelled_size"], 10)


class TestTimeInForce(unittest.TestCase):
    def setUp(self) -> None:
        self.book = create_order_book()

    def test_ioc_cancels_entire_order_without_liquidity(self) -> None:
        order = self.book.submit_order(
            limit_request(
                request_id=1,
                client_id=10,
                side=Side.BUY,
                price=100,
                size=10,
                time_in_force=TimeInForce.IOC
            )
        )

        self.assertEqual(order.status, OrderStatus.CANCELLED)
        self.assertEqual(order.size, 0)
        self.assertFalse(self.book.has_order(order.order_id))

        event = self.book.events[-1]

        self.assertEqual(event.event_type, EventType.ORDER_REMAINDER_CANCELLED)
        self.assertEqual(event.details["cancelled_size"], 10)

    def test_ioc_partially_fills_and_cancels_remainder(self) -> None:
        maker = self.book.submit_order(
            limit_request(1, 10, Side.SELL, 100, 4)
        )

        taker = self.book.submit_order(
            limit_request(
                request_id=2,
                client_id=20,
                side=Side.BUY,
                price=100,
                size=10,
                time_in_force=TimeInForce.IOC
            )
        )

        self.assertEqual(maker.status, OrderStatus.FILLED)
        self.assertEqual(taker.status, OrderStatus.CANCELLED)
        self.assertEqual(taker.size, 0)

        event = self.book.events[-1]

        self.assertEqual(event.event_type, EventType.ORDER_REMAINDER_CANCELLED)
        self.assertEqual(event.details["cancelled_size"], 6)

    def test_fok_cancels_without_partial_execution(self) -> None:
        maker = self.book.submit_order(
            limit_request(1, 10, Side.SELL, 100, 5)
        )

        fok_order = self.book.submit_order(
            limit_request(
                request_id=2,
                client_id=20,
                side=Side.BUY,
                price=100,
                size=10,
                time_in_force=TimeInForce.FOK
            )
        )

        self.assertEqual(fok_order.status, OrderStatus.CANCELLED)
        self.assertEqual(fok_order.size, 0)

        self.assertEqual(maker.status, OrderStatus.ACTIVE)
        self.assertEqual(maker.size, 5)

        trade_events = [
            event
            for event in self.book.events
            if event.event_type is EventType.TRADE_EXECUTED
        ]

        self.assertEqual(trade_events, [])

    def test_fok_fills_when_full_liquidity_exists(self) -> None:
        self.book.submit_order(
            limit_request(1, 10, Side.SELL, 100, 5)
        )
        self.book.submit_order(
            limit_request(2, 20, Side.SELL, 101, 5)
        )

        fok_order = self.book.submit_order(
            limit_request(
                request_id=3,
                client_id=30,
                side=Side.BUY,
                price=101,
                size=10,
                time_in_force=TimeInForce.FOK
            )
        )

        self.assertEqual(fok_order.status, OrderStatus.FILLED)
        self.assertEqual(fok_order.size, 0)
        self.assertTrue(self.book.is_empty())

        trade_events = [
            event
            for event in self.book.events
            if event.event_type is EventType.TRADE_EXECUTED
        ]

        self.assertEqual(len(trade_events), 2)

    def test_fok_ignores_liquidity_beyond_limit_price(self) -> None:
        maker = self.book.submit_order(
            limit_request(1, 10, Side.SELL, 101, 10)
        )

        fok_order = self.book.submit_order(
            limit_request(
                request_id=2,
                client_id=20,
                side=Side.BUY,
                price=100,
                size=10,
                time_in_force=TimeInForce.FOK
            )
        )

        self.assertEqual(fok_order.status, OrderStatus.CANCELLED)
        self.assertEqual(maker.status, OrderStatus.ACTIVE)
        self.assertEqual(maker.size, 10)


class TestCancellation(unittest.TestCase):
    def setUp(self) -> None:
        self.book = create_order_book()

    def test_cancel_removes_order_from_book_and_index(self) -> None:
        order = self.book.submit_order(
            limit_request(1, 10, Side.BUY, 100, 10)
        )

        event = self.book.cancel_order(
            CancelOrderRequest(
                request_id=2,
                client_id=10,
                order_id=order.order_id
            )
        )

        self.assertEqual(order.status, OrderStatus.CANCELLED)
        self.assertEqual(order.size, 0)

        self.assertFalse(self.book.has_order(order.order_id))
        self.assertTrue(self.book.is_empty())
        self.assertIsNone(self.book.get_best_bid_price())

        self.assertEqual(
            event.event_type,
            EventType.ORDER_CANCELLED
        )
        self.assertEqual(event.details["cancelled_size"], 10)

    def test_cancel_one_order_keeps_other_orders(self) -> None:
        first = self.book.submit_order(
            limit_request(1, 10, Side.BUY, 100, 10)
        )
        second = self.book.submit_order(
            limit_request(2, 20, Side.BUY, 100, 20)
        )

        self.book.cancel_order(
            CancelOrderRequest(
                request_id=3,
                client_id=10,
                order_id=first.order_id
            )
        )

        self.assertFalse(self.book.has_order(first.order_id))
        self.assertTrue(self.book.has_order(second.order_id))

        self.assertEqual(self.book.get_orders_at_price(Side.BUY, 100), [second])
        self.assertEqual(self.book.get_depth_at_price(Side.BUY, 100), 20)

    def test_cancel_unknown_order_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            self.book.cancel_order(
                CancelOrderRequest(
                    request_id=1,
                    client_id=10,
                    order_id=999
                )
            )

        self.assertEqual(self.book.events[-1].event_type, EventType.CANCEL_REJECTED)

    def test_wrong_client_cancel_is_rejected(self) -> None:
        order = self.book.submit_order(
            limit_request(1, 10, Side.BUY, 100, 10)
        )

        with self.assertRaises(ValueError):
            self.book.cancel_order(
                CancelOrderRequest(
                    request_id=2,
                    client_id=20,
                    order_id=order.order_id
                )
            )

        self.assertTrue(self.book.has_order(order.order_id))
        self.assertEqual(self.book.events[-1].event_type, EventType.CANCEL_REJECTED)


class TestModification(unittest.TestCase):
    def setUp(self) -> None:
        self.book = create_order_book()

    def test_size_decrease_keeps_fifo_priority(self) -> None:
        first = self.book.submit_order(
            limit_request(1, 10, Side.BUY, 100, 10)
        )
        second = self.book.submit_order(
            limit_request(2, 20, Side.BUY, 100, 10)
        )

        self.book.modify_order(
            ModifyOrderRequest(
                request_id=3,
                client_id=10,
                order_id=first.order_id,
                new_price=None,
                new_size=5
            )
        )

        self.assertEqual(first.size, 5)
        self.assertEqual(self.book.get_orders_at_price(Side.BUY, 100), [first, second])
        self.assertEqual(self.book.get_depth_at_price(Side.BUY, 100), 15)

    def test_size_increase_loses_fifo_priority(self) -> None:
        first = self.book.submit_order(
            limit_request(1, 10, Side.BUY, 100, 10)
        )
        second = self.book.submit_order(
            limit_request(2, 20, Side.BUY, 100, 10)
        )

        self.book.modify_order(
            ModifyOrderRequest(
                request_id=3,
                client_id=10,
                order_id=first.order_id,
                new_price=None,
                new_size=15
            )
        )

        self.assertEqual(first.size, 15)
        self.assertEqual(self.book.get_orders_at_price(Side.BUY, 100), [second, first])

    def test_price_change_moves_order_to_new_level(self) -> None:
        order = self.book.submit_order(
            limit_request(1, 10, Side.BUY, 100, 10)
        )

        self.book.modify_order(
            ModifyOrderRequest(
                request_id=2,
                client_id=10,
                order_id=order.order_id,
                new_price=105,
                new_size=None
            )
        )

        self.assertEqual(order.price, 105)
        self.assertEqual(self.book.get_depth_at_price(Side.BUY, 100), 0)
        self.assertEqual(self.book.get_depth_at_price(Side.BUY, 105), 10)
        self.assertEqual(self.book.get_best_bid_price(), 105)

    def test_price_change_can_cross_and_fill(self) -> None:
        ask = self.book.submit_order(
            limit_request(1, 10, Side.SELL, 101, 10)
        )
        bid = self.book.submit_order(
            limit_request(2, 20, Side.BUY, 100, 10)
        )

        self.book.modify_order(
            ModifyOrderRequest(
                request_id=3,
                client_id=20,
                order_id=bid.order_id,
                new_price=101,
                new_size=None
            )
        )

        self.assertEqual(ask.status, OrderStatus.FILLED)
        self.assertEqual(bid.status, OrderStatus.FILLED)

        self.assertFalse(self.book.has_order(ask.order_id))
        self.assertFalse(self.book.has_order(bid.order_id))
        self.assertTrue(self.book.is_empty())

    def test_rejected_modify_does_not_change_order(self) -> None:
        order = self.book.submit_order(
            limit_request(1, 10, Side.BUY, 100, 10)
        )

        with self.assertRaises(ValueError):
            self.book.modify_order(
                ModifyOrderRequest(
                    request_id=2,
                    client_id=20,
                    order_id=order.order_id,
                    new_price=105,
                    new_size=None
                )
            )

        self.assertEqual(order.price, 100)
        self.assertEqual(order.size, 10)
        self.assertTrue(self.book.has_order(order.order_id))

        self.assertEqual(self.book.events[-1].event_type, EventType.MODIFY_REJECTED)


class TestBookQueries(unittest.TestCase):
    def setUp(self) -> None:
        self.book = create_order_book()

    def test_get_order_and_order_node(self) -> None:
        order = self.book.submit_order(
            limit_request(1, 10, Side.BUY, 100, 10)
        )

        self.assertIs(self.book.get_order(order.order_id), order)

        node = self.book.get_order_node(order.order_id)

        self.assertIsNotNone(node)
        assert node is not None
        self.assertIs(node.order, order)

    def test_unknown_order_returns_none(self) -> None:
        self.assertIsNone(self.book.get_order(999))
        self.assertIsNone(self.book.get_order_node(999))
        self.assertFalse(self.book.has_order(999))

    def test_get_orders_at_price_returns_fifo_order(self) -> None:
        first = self.book.submit_order(
            limit_request(1, 10, Side.BUY, 100, 10)
        )
        second = self.book.submit_order(
            limit_request(2, 20, Side.BUY, 100, 20)
        )

        self.assertEqual(self.book.get_orders_at_price(Side.BUY, 100), [first, second])

    def test_side_snapshot_is_best_to_worst(self) -> None:
        self.book.submit_order(
            limit_request(1, 10, Side.BUY, 99, 10)
        )
        self.book.submit_order(
            limit_request(2, 20, Side.BUY, 101, 20)
        )
        self.book.submit_order(
            limit_request(3, 30, Side.BUY, 100, 30)
        )

        snapshot = self.book.get_side_snapshot(Side.BUY)

        self.assertEqual([level["price"] for level in snapshot], [101, 100, 99])

    def test_book_snapshot_contains_top_of_book(self) -> None:
        self.book.submit_order(
            limit_request(1, 10, Side.BUY, 100, 10)
        )
        self.book.submit_order(
            limit_request(2, 20, Side.SELL, 105, 20)
        )

        snapshot = self.book.get_book_snapshot()

        self.assertEqual(snapshot["symbol"], "TEST")
        self.assertEqual(snapshot["best_bid_price"], 100)
        self.assertEqual(snapshot["best_bid_size"], 10)
        self.assertEqual(snapshot["best_ask_price"], 105)
        self.assertEqual(snapshot["best_ask_size"], 20)
        self.assertEqual(snapshot["spread"], 5)
        self.assertEqual(snapshot["mid_price"], 102.5)
        self.assertEqual(snapshot["active_order_count"], 2)


class TestEventsAndIdentifiers(unittest.TestCase):
    def setUp(self) -> None:
        self.book = create_order_book()

    def test_order_ids_are_sequential(self) -> None:
        first = self.book.submit_order(
            limit_request(1, 10, Side.BUY, 99, 10)
        )
        second = self.book.submit_order(
            limit_request(2, 20, Side.BUY, 100, 10)
        )

        self.assertEqual(first.order_id, 1)
        self.assertEqual(second.order_id, 2)
        self.assertEqual(self.book.next_order_id, 3)

    def test_trade_ids_are_sequential(self) -> None:
        self.book.submit_order(
            limit_request(1, 10, Side.SELL, 100, 5)
        )
        self.book.submit_order(
            limit_request(2, 20, Side.SELL, 101, 5)
        )
        self.book.submit_order(
            market_request(3, 30, Side.BUY, 10)
        )

        trade_ids = [
            event.details["trade_id"]
            for event in self.book.events
            if event.event_type is EventType.TRADE_EXECUTED
        ]

        self.assertEqual(trade_ids, [1, 2])
        self.assertEqual(self.book.next_trade_id, 3)

    def test_event_sequences_are_contiguous(self) -> None:
        self.book.submit_order(
            limit_request(1, 10, Side.BUY, 100, 10)
        )
        self.book.submit_order(
            limit_request(2, 20, Side.SELL, 105, 10)
        )

        sequences = [
            event.sequence
            for event in self.book.events
        ]

        self.assertEqual(sequences, list(range(1, len(sequences) + 1)))

    def test_event_details_include_symbol(self) -> None:
        self.book.submit_order(
            limit_request(1, 10, Side.BUY, 100, 10)
        )

        for event in self.book.events:
            self.assertEqual(event.details["symbol"], "TEST")


class TestReset(unittest.TestCase):
    def test_reset_clears_state_and_identifiers(self) -> None:
        book = create_order_book()

        book.submit_order(
            limit_request(1, 10, Side.BUY, 100, 10)
        )

        book.reset()

        self.assertTrue(book.is_empty())
        self.assertEqual(book.order_index, {})
        self.assertEqual(book.events, [])

        self.assertEqual(book.next_order_id, 1)
        self.assertEqual(book.next_trade_id, 1)
        self.assertEqual(book.event_sequence, 1)


if __name__ == "__main__":
    unittest.main()
