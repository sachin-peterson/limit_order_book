import unittest

from order_book_python.simulation.clock import SimulationClock


class TestSimulationClock(unittest.TestCase):
    def test_clock_starts_at_configured_value(self) -> None:
        clock = SimulationClock(start=100)

        self.assertEqual(clock(), 100)

    def test_clock_increments_by_step(self) -> None:
        clock = SimulationClock(start=100, step=5)

        self.assertEqual(clock(), 100)
        self.assertEqual(clock(), 105)
        self.assertEqual(clock(), 110)

    def test_rejects_negative_start(self) -> None:
        with self.assertRaises(ValueError):
            SimulationClock(start=-1)

    def test_rejects_non_positive_step(self) -> None:
        with self.assertRaises(ValueError):
            SimulationClock(step=0)

        with self.assertRaises(ValueError):
            SimulationClock(step=-1)


if __name__ == "__main__":
    unittest.main()
