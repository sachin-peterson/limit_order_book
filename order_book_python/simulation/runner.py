from __future__ import annotations

from collections.abc import Callable

from order_book_python.engine.matching_engine import OrderBook
from order_book_python.engine.state_validation import validate_state
from order_book_python.engine.types.events import Event
from order_book_python.engine.types.instruments import Instrument
from order_book_python.engine.types.requests import CancelOrderRequest, ModifyOrderRequest, NewOrderRequest

from .config import SimulationConfig
from .generator import SimulationRequest, StochasticRequestGenerator


class SimulationRunner:
    """
    Runs a stochastic order-book simulation.

    Attributes:
    - validate_after_each_request: whether the book is validated after request
    - clock: optional clock passed to the matching engine
    """

    def __init__(
        self,
        validate_after_each_request: bool = False,
        clock: Callable[[], int] | None = None
    ) -> None:
        self.validate_after_each_request = validate_after_each_request
        self.clock = clock

    def run(
        self,
        instrument: Instrument,
        config: SimulationConfig,
        on_event: Callable[[Event], None] | None = None,
        on_step: Callable[[OrderBook], None] | None = None
    ) -> OrderBook:
        order_book = OrderBook(
            instrument=instrument,
            clock=self.clock
        )
        generator = StochasticRequestGenerator(config)

        for _ in range(config.action_count):
            request = generator.generate_request(order_book)
            event_start = len(order_book.events)

            try:
                self.process_request(order_book, request)
            except ValueError:
                pass

            if self.validate_after_each_request:
                validate_state(order_book)

            new_events = order_book.events[event_start:]

            if on_event is not None:
                for event in new_events:
                    on_event(event)

            if on_step is not None:
                on_step(order_book)

        if on_step is not None:
            on_step(order_book)

        return order_book

    def process_request(self, order_book: OrderBook, request: SimulationRequest) -> None:
        if isinstance(request, NewOrderRequest):
            order_book.submit_order(request)
            return

        if isinstance(request, CancelOrderRequest):
            order_book.cancel_order(request)
            return

        if isinstance(request, ModifyOrderRequest):
            order_book.modify_order(request)
            return

        raise TypeError("Unsupported simulation request")
