import unittest

from order_book_python.engine.types.enums import OrderType, TimeInForce
from order_book_python.engine.types.requests import CancelOrderRequest, ModifyOrderRequest, NewOrderRequest
from order_book_python.simulation.config import SimulationConfig
from order_book_python.simulation.generator import StochasticRequestGenerator

from .helpers import create_book, insert_resting_order, request_signature


class TestStochasticRequestGenerator(unittest.TestCase):
    def test_empty_book_always_generates_new_order(self) -> None:
        config = SimulationConfig(
            seed=42,
            new_order_probability=0.0,
            cancel_probability=1.0,
            modify_probability=0.0
        )

        generator = StochasticRequestGenerator(config)
        request = generator.generate_request(create_book())

        self.assertIsInstance(request, NewOrderRequest)

    def test_same_seed_generates_same_requests(self) -> None:
        config = SimulationConfig(
            seed=42,
            new_order_probability=1.0,
            cancel_probability=0.0,
            modify_probability=0.0
        )

        first_generator = StochasticRequestGenerator(config)
        second_generator = StochasticRequestGenerator(config)

        first_book = create_book()
        second_book = create_book()

        first_requests = [
            request_signature(
                first_generator.generate_request(first_book)
            )
            for _ in range(20)
        ]

        second_requests = [
            request_signature(
                second_generator.generate_request(second_book)
            )
            for _ in range(20)
        ]

        self.assertEqual(first_requests, second_requests)

    def test_cancel_request_targets_active_order(self) -> None:
        book = create_book()
        insert_resting_order(book)

        config = SimulationConfig(
            seed=42,
            new_order_probability=0.0,
            cancel_probability=1.0,
            modify_probability=0.0
        )

        generator = StochasticRequestGenerator(config)
        request = generator.generate_request(book)

        self.assertIsInstance(request, CancelOrderRequest)
        assert isinstance(request, CancelOrderRequest)

        order = book.get_order(request.order_id)

        self.assertIsNotNone(order)
        assert order is not None

        self.assertEqual(request.client_id, order.client_id)

    def test_modify_request_targets_active_order(self) -> None:
        book = create_book()
        insert_resting_order(book)

        config = SimulationConfig(
            seed=42,
            new_order_probability=0.0,
            cancel_probability=0.0,
            modify_probability=1.0
        )

        generator = StochasticRequestGenerator(config)
        request = generator.generate_request(book)

        self.assertIsInstance(request, ModifyOrderRequest)
        assert isinstance(request, ModifyOrderRequest)

        order = book.get_order(request.order_id)

        self.assertIsNotNone(order)
        assert order is not None

        self.assertEqual(request.client_id, order.client_id)

        changed_price = (
            request.new_price is not None
            and request.new_price != order.price
        )

        changed_size = (
            request.new_size is not None
            and request.new_size != order.size
        )

        self.assertTrue(changed_price or changed_size)

    def test_generated_size_respects_lot_size(self) -> None:
        book = create_book()

        config = SimulationConfig(
            seed=42,
            new_order_probability=1.0,
            cancel_probability=0.0,
            modify_probability=0.0
        )

        generator = StochasticRequestGenerator(config)

        for _ in range(100):
            request = generator.generate_new_order(book)
            
            self.assertEqual(request.size % book.instrument.lot_size, 0)

    def test_limit_price_respects_tick_size(self) -> None:
        book = create_book()

        config = SimulationConfig(
            seed=42,
            new_order_probability=1.0,
            cancel_probability=0.0,
            modify_probability=0.0,
            market_order_probability=0.0
        )

        generator = StochasticRequestGenerator(config)

        for _ in range(100):
            request = generator.generate_new_order(book)

            self.assertEqual(request.order_type, OrderType.LIMIT)
            self.assertIsNotNone(request.price)

            assert request.price is not None

            self.assertEqual(request.price % book.instrument.tick_size, 0)

    def test_market_orders_have_no_price(self) -> None:
        book = create_book()

        config = SimulationConfig(
            seed=42,
            new_order_probability=1.0,
            cancel_probability=0.0,
            modify_probability=0.0,
            market_order_probability=1.0
        )

        generator = StochasticRequestGenerator(config)

        for _ in range(20):
            request = generator.generate_new_order(book)

            self.assertEqual(request.order_type, OrderType.MARKET)
            self.assertIsNone(request.price)
            self.assertIn(request.time_in_force, [TimeInForce.IOC, TimeInForce.FOK])

    def test_request_ids_are_sequential(self) -> None:
        generator = StochasticRequestGenerator(
            SimulationConfig(seed=42)
        )

        self.assertEqual(generator.generate_request_id(), 1)
        self.assertEqual(generator.generate_request_id(), 2)
        self.assertEqual(generator.generate_request_id(), 3)


if __name__ == "__main__":
    unittest.main()
