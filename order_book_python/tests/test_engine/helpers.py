from order_book_python.engine.matching_engine import OrderBook
from order_book_python.engine.types.enums import OrderStatus, OrderType, Side, TimeInForce
from order_book_python.engine.types.instruments import Instrument
from order_book_python.engine.types.requests import NewOrderRequest
from order_book_python.engine.types.orders import Order

class IncrementingClock:
    def __init__(self, start: int = 1_000_000) -> None:
        self.current = start

    def __call__(self) -> int:
        timestamp = self.current
        self.current += 1
        return timestamp

def create_order_book(
        tick_size: int = 1, 
        lot_size: int = 1
) -> OrderBook:
    test_instrument = Instrument(
        symbol="TEST",
        tick_size=tick_size,
        lot_size=lot_size
    )

    return OrderBook(
        instrument=test_instrument,
        clock=IncrementingClock()
    )

def create_order(
    order_id: int,
    side: Side,
    price: int,
    size: int = 10,
    client_id: int = 1
) -> Order:
    return Order(
        order_id=order_id,
        request_id=order_id,
        client_id=client_id,
        side=side,
        order_type=OrderType.LIMIT,
        time_in_force=TimeInForce.GTC,
        size=size,
        timestamp=order_id,
        price=price,
        status=OrderStatus.ACTIVE
    )

def limit_request(
    request_id: int,
    client_id: int,
    side: Side,
    price: int,
    size: int,
    time_in_force: TimeInForce = TimeInForce.GTC
) -> NewOrderRequest:
    return NewOrderRequest(
        request_id=request_id,
        client_id=client_id,
        side=side,
        order_type=OrderType.LIMIT,
        size=size,
        time_in_force=time_in_force,
        price=price
    )

def market_request(
    request_id: int,
    client_id: int,
    side: Side,
    size: int,
    time_in_force: TimeInForce = TimeInForce.IOC
) -> NewOrderRequest:
    return NewOrderRequest(
        request_id=request_id,
        client_id=client_id,
        side=side,
        order_type=OrderType.MARKET,
        size=size,
        time_in_force=time_in_force,
        price=None
    )
