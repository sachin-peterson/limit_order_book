class SimulationConfig:
    """
    Configuration for a stochastic order-book simulation

    Attributes:
    - action_count: number of requests generated during simulation
    - seed: random seed used to reproduce a simulation
    - initial_price: reference price when book is empty
    - client_count: number of simulated clients
    - min_lot_count: minimum number of lots in a generated order
    - max_lot_count: maximum number of lots in a generated order
    - price_range_ticks: maximum price distance from the reference price
    - new_order_probability: P(generate new order)
    - cancel_probability: P(generate a cancellation)
    - modify_probability: P(generate a modificaation)
    - buy_probability: P(new order is a buy order)
    - market_order_probability: P(new order is a market order)
    """
    def __init__(
        self,
        action_count: int = 1_000,
        seed: int | None = None,
        initial_price: int = 10_000,
        client_count: int = 100,
        min_lot_count: int = 1,
        max_lot_count: int = 100,
        price_range_ticks: int = 20,
        new_order_probability: float = 0.75,
        cancel_probability: float = 0.15,
        modify_probability: float = 0.10,
        buy_probability: float = 0.50,
        market_order_probability: float = 0.10
    ) -> None:
        if not isinstance(action_count, int) or action_count <= 0:
            raise ValueError("Action count must be a positive integer")

        if seed is not None and not isinstance(seed, int):
            raise ValueError("Seed must be an integer or None")

        if not isinstance(initial_price, int) or initial_price <= 0:
            raise ValueError("Initial price must be a positive integer")

        if not isinstance(client_count, int) or client_count <= 0:
            raise ValueError("Client count must be a positive integer")

        if not isinstance(min_lot_count, int) or min_lot_count <= 0:
            raise ValueError("Minimum lot count must be positive")

        if not isinstance(max_lot_count, int) or max_lot_count <= 0:
            raise ValueError("Maximum lot count must be positive")

        if min_lot_count > max_lot_count:
            raise ValueError("Minimum lot count cannot exceed maximum lot count")

        if not isinstance(price_range_ticks, int) or price_range_ticks < 0:
            raise ValueError("Price range in ticks must be a non-negative integer")

        action_probability_total = (
            new_order_probability
            + cancel_probability
            + modify_probability
        )

        if abs(action_probability_total - 1.0) > 1e-9:
            raise ValueError("New, cancel, and modify probabilities must sum to 1")

        probabilities = {
            "New order probability": new_order_probability,
            "Cancel probability": cancel_probability,
            "Modify probability": modify_probability,
            "Buy probability": buy_probability,
            "Market order probability": market_order_probability,
        }

        for name, probability in probabilities.items():
            if not isinstance(probability, (int, float)):
                raise ValueError(f"{name} must be numeric")

            if probability < 0 or probability > 1:
                raise ValueError(f"{name} must be between 0 and 1")

        self.action_count = action_count
        self.seed = seed
        self.initial_price = initial_price
        self.client_count = client_count

        self.min_lot_count = min_lot_count
        self.max_lot_count = max_lot_count
        self.price_range_ticks = price_range_ticks

        self.new_order_probability = new_order_probability
        self.cancel_probability = cancel_probability
        self.modify_probability = modify_probability

        self.buy_probability = buy_probability
        self.market_order_probability = market_order_probability
