from .price_level import OrderNode
from .types.enums import OrderType, TimeInForce
from .types.instruments import Instrument
from .types.requests import CancelOrderRequest, ModifyOrderRequest, NewOrderRequest

SUPPORTED_COMBINATIONS = {
    (OrderType.LIMIT, TimeInForce.IOC),
    (OrderType.LIMIT, TimeInForce.GTC),
    (OrderType.LIMIT, TimeInForce.FOK),
    (OrderType.MARKET, TimeInForce.IOC),
    (OrderType.MARKET, TimeInForce.FOK)
    # MARKET GTC is an invalid combination
}

def validate_new_order(
    request: NewOrderRequest, 
    instrument: Instrument
) -> None:
    if request.size % instrument.lot_size != 0:
        raise ValueError("Order size must be a multiple of lot size")

    combination = (request.order_type, request.time_in_force)

    if combination not in SUPPORTED_COMBINATIONS:
        raise ValueError("Unsupported order type and time-in-force combination")

    if request.order_type is OrderType.LIMIT:
        if request.price is None or request.price <= 0:
            raise ValueError("Limit order price must be positive")

        if request.price % instrument.tick_size != 0:
            raise ValueError("Limit order price must be a multiple of tick size")

    elif request.order_type is OrderType.MARKET:
        if request.price is not None:
            raise ValueError("Market order price must be None")

def validate_cancel_request(
    request: CancelOrderRequest, 
    order_index: dict[int, OrderNode]
) -> None:
    if request.order_id not in order_index:
        raise ValueError("Order does not exist")

    order_node = order_index[request.order_id]

    if request.client_id != order_node.order.client_id:
        raise ValueError("Order does not belong to client")

def validate_modify_request(
    request: ModifyOrderRequest,
    instrument: Instrument,
    order_index: dict[int, OrderNode]
) -> None:
    if request.order_id not in order_index:
        raise ValueError("Order does not exist")

    order = order_index[request.order_id].order

    if request.client_id != order.client_id:
        raise ValueError("Order does not belong to client")

    if request.new_price is None and request.new_size is None:
        raise ValueError("Modify request must alter price, size, or both")

    target_price = order.price if request.new_price is None else request.new_price
    target_size = order.size if request.new_size is None else request.new_size

    if target_price == order.price and target_size == order.size:
        raise ValueError("Modify request does not change the order")

    if request.new_price is not None and request.new_price % instrument.tick_size != 0:
        raise ValueError("New price must be a multiple of tick size")

    if request.new_size is not None and request.new_size % instrument.lot_size != 0:
        raise ValueError("New size must be a multiple of lot size")
