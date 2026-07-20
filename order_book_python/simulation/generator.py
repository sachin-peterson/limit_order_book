from __future__ import annotations

import random

from order_book_python.engine.matching_engine import OrderBook
from order_book_python.engine.types.enums import OrderType, Side, TimeInForce
from order_book_python.engine.types.requests import CancelOrderRequest, ModifyOrderRequest, NewOrderRequest

from .config import SimulationConfig


SimulationRequest = NewOrderRequest | CancelOrderRequest | ModifyOrderRequest


class StochasticRequestGenerator:
    """
    Generates stochastic requests based on the current book state
    
    Attributes:
    - config: stochastic simulation configuration
    """
    def __init__(
        self, 
        config: SimulationConfig
    ) -> None:
        self.config = config
        self.rng = random.Random(config.seed)
        self.next_request_id = 1

    def generate_request(self, order_book: OrderBook) -> SimulationRequest:
        action_type = self.choose_action_type(order_book)

        if action_type == "NEW":
            return self.generate_new_order(order_book)

        if action_type == "CANCEL":
            return self.generate_cancel_order(order_book)

        return self.generate_modify_order(order_book)
    
    def choose_action_type(self, order_book: OrderBook) -> str:
        if not order_book.order_index:
            return "NEW"

        value = self.rng.random()

        new_limit = self.config.new_order_probability
        cancel_limit = new_limit + self.config.cancel_probability

        if value < new_limit:
            return "NEW"

        if value < cancel_limit:
            return "CANCEL"

        return "MODIFY"

    def generate_new_order(self, order_book: OrderBook) -> NewOrderRequest:
        side = self.generate_side()
        size = self.generate_size(order_book)
        client_id = self.rng.randint(1, self.config.client_count)

        is_market_order = self.rng.random() < self.config.market_order_probability

        if is_market_order:
            order_type = OrderType.MARKET
            time_in_force = self.rng.choices(
                [
                    TimeInForce.IOC,
                    TimeInForce.FOK
                ],
                weights=[0.50, 0.50],
                k=1
            )[0]
            price = None
        else:
            order_type = OrderType.LIMIT
            time_in_force = self.rng.choices(
                [
                    TimeInForce.GTC,
                    TimeInForce.IOC,
                    TimeInForce.FOK,
                ],
                weights=[0.80, 0.15, 0.05],
                k=1
            )[0]
            price = self.generate_price(
                order_book,
                side
            )

        return NewOrderRequest(
            request_id=self.generate_request_id(),
            client_id=client_id,
            side=side,
            order_type=order_type,
            size=size,
            time_in_force=time_in_force,
            price=price
        )
    
    def generate_cancel_order(self, order_book: OrderBook) -> CancelOrderRequest:
        order_node = self.rng.choice(
            list(order_book.order_index.values())
        )

        order = order_node.order

        return CancelOrderRequest(
            request_id=self.generate_request_id(),
            client_id=order.client_id,
            order_id=order.order_id
        )

    def generate_modify_order(self, order_book: OrderBook) -> ModifyOrderRequest:
        order_node = self.rng.choice(
            list(order_book.order_index.values())
        )

        order = order_node.order
        change_price = self.rng.random() < 0.5

        if change_price:
            new_price = self.generate_different_price(
                order_book,
                order.price
            )
            new_size = None
        else:
            new_size = self.generate_different_size(
                order_book,
                order.size
            )

            if new_size is None:
                new_price = self.generate_different_price(
                    order_book,
                    order.price
                )
            else:
                new_price = None

        return ModifyOrderRequest(
            request_id=self.generate_request_id(),
            client_id=order.client_id,
            order_id=order.order_id,
            new_price=new_price,
            new_size=new_size
        )

    def generate_side(self) -> Side:
        if self.rng.random() < self.config.buy_probability:
            return Side.BUY

        return Side.SELL

    def generate_size(self, order_book: OrderBook) -> int:
        lot_count = self.rng.randint(
            self.config.min_lot_count,
            self.config.max_lot_count
        )

        return lot_count * order_book.instrument.lot_size
    
    def generate_different_size(self, order_book: OrderBook, current_size: int) -> int | None:
        minimum_size = self.config.min_lot_count * order_book.instrument.lot_size
        maximum_size = self.config.max_lot_count * order_book.instrument.lot_size

        if minimum_size == maximum_size == current_size:
            return None

        new_size = self.generate_size(order_book)

        if new_size == current_size:
            if current_size != minimum_size:
                return minimum_size

            return maximum_size

        return new_size
    
    def generate_price(self, order_book: OrderBook, side: Side) -> int:
        tick_size = order_book.instrument.tick_size
        reference_price = self.get_reference_price(order_book)

        offset = self.rng.randint(0, self.config.price_range_ticks)

        if side is Side.BUY:
            price = reference_price - offset * tick_size
        else:
            price = reference_price + offset * tick_size

        return max(price, tick_size)

    def generate_different_price(self, order_book: OrderBook, current_price: int | None) -> int:
        if current_price is None:
            raise RuntimeError("Resting order has no price")

        side = Side.BUY if self.rng.random() < 0.5 else Side.SELL

        new_price = self.generate_price(order_book, side)

        if new_price == current_price:
            tick_size = order_book.instrument.tick_size

            if current_price > tick_size:
                return current_price - tick_size

            return current_price + tick_size

        return new_price

    def get_reference_price(self, order_book: OrderBook) -> int:
        tick_size = order_book.instrument.tick_size
        mid_price = order_book.get_mid_price()

        if mid_price is not None:
            tick_count = round(mid_price / tick_size)
            return max(tick_count * tick_size, tick_size)

        best_bid = order_book.get_best_bid_price()

        if best_bid is not None:
            return best_bid

        best_ask = order_book.get_best_ask_price()

        if best_ask is not None:
            return best_ask

        tick_count = round(self.config.initial_price / tick_size)

        return max(tick_count * tick_size, tick_size)

    def generate_request_id(self) -> int:
        request_id = self.next_request_id
        self.next_request_id += 1
        return request_id
