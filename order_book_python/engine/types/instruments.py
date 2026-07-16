class Instrument:
    """
    Represents a tradable financial instrument

    Attributes:
    - symbol: instrument identifier (e.g., AAPL, NVDA)
    - tick_size: smallest permitted price increment 
    - lot_size : smallest permitted order-size increment
    """
    def __init__(
        self,
        symbol: str,
        tick_size: int = 1,
        lot_size: int = 1
    ) -> None:
        if not isinstance(symbol, str) or not symbol.strip():
            raise ValueError("Symbol must be a non-empty string")

        if not isinstance(tick_size, int) or tick_size <= 0:
            raise ValueError("Tick size must be a positive integer")

        if not isinstance(lot_size, int) or lot_size <= 0:
            raise ValueError("Lot size must be a positive integer")
        
        self.symbol = symbol.strip().upper()
        self.tick_size = tick_size
        self.lot_size = lot_size
