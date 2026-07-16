from .enums import Side


class Order:
    """
    Represents an order accepted by the matching engine
    
    Attributes:
    - order_id: unique identifier assigned by the engine
    - client_id: identifier of the client that submitted the order
    - side: "BUY" or "SELL"
    - size: remaining unfilled quantity
    - timestamp: time used to determine order priority
    - price: limit price, or None for a market order
    """
    def __init__(
        self,
        order_id: int,
        client_id: int,
        side: Side,
        size: int,
        timestamp: int,
        price: int | None = None
    ) -> None:
        if not isinstance(order_id, int) or order_id <= 0:
            raise ValueError("Order ID must be positive")
        
        if not isinstance(client_id, int) or client_id <= 0:
            raise ValueError("Client ID must be positive")
        
        if not isinstance(side, Side):
            raise ValueError("Side must be BUY or SELL")
        
        if price is not None:
            if not isinstance(price, int) or price <= 0:
                raise ValueError("Price must be a positive integer or None")
        
        if not isinstance(size, int) or size <= 0:
            raise ValueError("Size must be a positive integer")
        
        if not isinstance(timestamp, int) or timestamp < 0:
            raise ValueError("Timestamp must be a non-negative integer")
        
        self.order_id = order_id
        self.client_id = client_id
        self.side = side
        self.price = price
        self.size = size
        self.timestamp = timestamp
