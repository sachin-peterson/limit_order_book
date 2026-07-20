from order_book_python.engine.matching_engine import OrderBook
from order_book_python.engine.types.enums import OrderType, Side, TimeInForce
from order_book_python.engine.types.instruments import Instrument
from order_book_python.engine.types.events import Event
from order_book_python.engine.types.requests import CancelOrderRequest, NewOrderRequest
from order_book_python.simulation.clock import SimulationClock
from order_book_python.simulation.generator import SimulationRequest


def create_book() -> OrderBook:
    instrument = Instrument(
        symbol="TEST",
        tick_size=5,
        lot_size=10
    )

    return OrderBook(
        instrument=instrument,
        clock=SimulationClock()
    )

def insert_resting_order(order_book: OrderBook) -> None:
    order_book.submit_order(
        NewOrderRequest(
            request_id=100,
            client_id=10,
            side=Side.BUY,
            order_type=OrderType.LIMIT,
            size=20,
            time_in_force=TimeInForce.GTC,
            price=100
        )
    )

def request_signature(request: SimulationRequest) -> tuple[object, ...]:
    if isinstance(request, NewOrderRequest):
        return (
            "NEW",
            request.request_id,
            request.client_id,
            request.side,
            request.order_type,
            request.size,
            request.time_in_force,
            request.price
        )

    if isinstance(request, CancelOrderRequest):
        return (
            "CANCEL",
            request.request_id,
            request.client_id,
            request.order_id
        )

    return (
        "MODIFY",
        request.request_id,
        request.client_id,
        request.order_id,
        request.new_price,
        request.new_size
    )

def create_instrument() -> Instrument:
    return Instrument(
        symbol="TEST",
        tick_size=1,
        lot_size=1
    )

def event_signature(event: Event) -> tuple[object, ...]:
    return (
        event.sequence,
        event.timestamp,
        event.event_type,
        event.details
    )
