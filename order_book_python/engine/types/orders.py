from .enums import Side, OrderType, TimeInForce, OrderStatus

class Order:
    """
    Represents an order accepted by the matching engine
    
    Attributes:
    - order_id: unique identifier assigned by the engine
    - request_id: identifier of the request that created the order
    - client_id: identifier of the client that submitted the order
    - order_type: "LIMIT" or "MARKET"
    - time_in_force: rule controlling order execution
    - side: "BUY" or "SELL"
    - size: remaining unfilled quantity
    - original_size: quantity originally submitted
    - timestamp: time used to determine order priority
    - price: limit price, or None for a market order
    - status: current state of the order
    """
    def __init__(
        self,
        order_id: int,
        request_id: int,
        client_id: int,
        side: Side,
        order_type: OrderType,
        time_in_force: TimeInForce,
        size: int,
        timestamp: int,
        price: int | None = None,
        status: OrderStatus = OrderStatus.ACTIVE
    ) -> None:
        if not isinstance(order_id, int) or order_id <= 0:
            raise ValueError("Order ID must be a positive integer")

        if not isinstance(request_id, int) or request_id <= 0:
            raise ValueError("Request ID must be a positive integer")

        if not isinstance(client_id, int) or client_id <= 0:
            raise ValueError("Client ID must be a positive integer")

        if not isinstance(side, Side):
            raise ValueError("Side must be BUY or SELL")

        if not isinstance(order_type, OrderType):
            raise ValueError("Order type must be LIMIT or MARKET")

        if not isinstance(time_in_force, TimeInForce):
            raise ValueError("Time in force must be GTC, IOC, or FOK")

        if not isinstance(size, int) or size <= 0:
            raise ValueError("Size must be a positive integer")

        if not isinstance(timestamp, int) or timestamp < 0:
            raise ValueError("Timestamp must be a non-negative integer")

        if price is not None:
            if not isinstance(price, int) or price <= 0:
                raise ValueError("Price must be a positive integer or None")

        if not isinstance(status, OrderStatus):
            raise ValueError("Status must be an OrderStatus")

        self.order_id = order_id
        self.request_id = request_id
        self.client_id = client_id
        self.side = side
        self.order_type = order_type
        self.time_in_force = time_in_force
        self.price = price
        self.size = size
        self.original_size = size
        self.timestamp = timestamp
        self.status = status
