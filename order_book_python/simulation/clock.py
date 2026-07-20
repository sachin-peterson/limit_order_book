class SimulationClock:
    """
    Provides deterministic timestamps during simulation

    Attributes:
    - current: timestamp that will be returned next
    - step: time amount added after each timestamp
    """
    def __init__(
        self,
        start: int = 0,
        step: int = 1
    ) -> None:
        if not isinstance(start, int) or start < 0:
            raise ValueError("Start must be a non-negative integer")

        if not isinstance(step, int) or step <= 0:
            raise ValueError("Step must be a positive integer")

        self.current = start
        self.step = step

    def __call__(self) -> int:
        timestamp = self.current
        self.current += self.step
        return timestamp
