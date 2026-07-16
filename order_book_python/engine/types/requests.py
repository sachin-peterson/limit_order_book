from .enums import Side, OrderType, TimeInForce


class NewOrderRequest:
    """
    Represents a request to submit a new order

    Attributes:
    - request_id: unique identifier for the request
    - client_id: identifier of the client submitting the order
    - side: "BUY" or "SELL"
    - order_type: "LIMIT" or "MARKET" (for now)
    - size: requested order quantity
    - time_in_force: rule controlling duration of order activity
    - price: limit price, or None for a market order
    """
    def __init__(
        self,
        request_id: int,
        client_id: int,
        side: Side,
        order_type: OrderType,
        size: int,
        time_in_force: TimeInForce,
        price: int | None = None
    ) -> None:
        if not isinstance(request_id, int) or request_id <= 0:
            raise ValueError("Request ID must be a positive integer")

        if not isinstance(client_id, int) or client_id <= 0:
            raise ValueError("Client ID must be a positive integer")

        if not isinstance(side, Side):
            raise ValueError("Side must be BUY or SELL")

        if not isinstance(order_type, OrderType):
            raise ValueError("Order type must be a valid OrderType")

        if not isinstance(size, int) or size <= 0:
            raise ValueError("Size must be a positive integer")

        if not isinstance(time_in_force, TimeInForce):
            raise ValueError("Time in force must be a valid TimeInForce")

        if price is not None:
            if not isinstance(price, int) or price <= 0:
                raise ValueError("Price must be a positive integer or None")

        self.request_id = request_id
        self.client_id = client_id
        self.side = side
        self.order_type = order_type
        self.size = size
        self.time_in_force = time_in_force
        self.price = price


class CancelOrderRequest:
    """
    Represents a request to cancel an new order
    
    Attributes:
    - request_id: unique identifier for the request
    - client_id: identifier of the client requesting the cancellation
    - order_id: identifier of the order to cancel
    """
    def __init__(
        self,
        request_id: int,
        client_id: int,
        order_id: int
    ) -> None:
        if not isinstance(request_id, int) or request_id <= 0:
            raise ValueError("Request ID must be a positive integer")

        if not isinstance(client_id, int) or client_id <= 0:
            raise ValueError("Client ID must be a positive integer")

        if not isinstance(order_id, int) or order_id <= 0:
            raise ValueError("Order ID must be a positive integer")

        self.request_id = request_id
        self.client_id = client_id
        self.order_id = order_id


class ModifyOrderRequest:
    """
    Represents a request to modify an existing order
    
    Attributes:
    - request_id: unique identifier for the request
    - client_id: identifier of the client requesting the modification
    - order_id: identifier of the order to modify
    - new_size: new order size, or None if unchanged
    - new_price: new order price, or None if unchanged
    """
    def __init__(
        self,
        request_id: int,
        client_id: int,
        order_id: int,
        new_size: int | None = None,
        new_price: int | None = None
    ) -> None:
        if not isinstance(request_id, int) or request_id <= 0:
            raise ValueError("Request ID must be a positive integer")

        if not isinstance(client_id, int) or client_id <= 0:
            raise ValueError("Client ID must be a positive integer")

        if not isinstance(order_id, int) or order_id <= 0:
            raise ValueError("Order ID must be a positive integer")

        if new_size is not None:
            if not isinstance(new_size, int) or new_size <= 0:
                raise ValueError("New size must be a positive integer")

        if new_price is not None:
            if not isinstance(new_price, int) or new_price <= 0:
                raise ValueError("New price must be a positive integer")

        self.request_id = request_id
        self.client_id = client_id
        self.order_id = order_id
        self.new_size = new_size
        self.new_price = new_price
