import unittest

from order_book_python.simulation.config import SimulationConfig


class TestSimulationConfig(unittest.TestCase):
    def test_default_configuration_is_valid(self) -> None:
        config = SimulationConfig()

        self.assertEqual(config.action_count, 1_000)
        self.assertIsNone(config.seed)
        self.assertEqual(config.initial_price, 10_000)
        self.assertEqual(config.client_count, 100)

    def test_stores_custom_values(self) -> None:
        config = SimulationConfig(
            action_count=500,
            seed=42,
            initial_price=5_000,
            client_count=20,
            min_lot_count=2,
            max_lot_count=50,
            price_range_ticks=10,
            new_order_probability=0.60,
            cancel_probability=0.25,
            modify_probability=0.15,
            buy_probability=0.55,
            market_order_probability=0.20
        )

        self.assertEqual(config.action_count, 500)
        self.assertEqual(config.seed, 42)
        self.assertEqual(config.initial_price, 5_000)
        self.assertEqual(config.client_count, 20)
        self.assertEqual(config.min_lot_count, 2)
        self.assertEqual(config.max_lot_count, 50)

    def test_rejects_invalid_action_count(self) -> None:
        with self.assertRaises(ValueError):
            SimulationConfig(action_count=0)

    def test_rejects_invalid_seed(self) -> None:
        with self.assertRaises(ValueError):
            SimulationConfig(seed="42")

    def test_rejects_invalid_lot_range(self) -> None:
        with self.assertRaises(ValueError):
            SimulationConfig(
                min_lot_count=10,
                max_lot_count=5
            )

    def test_rejects_action_probabilities_not_summing_to_one(self) -> None:
        with self.assertRaises(ValueError):
            SimulationConfig(
                new_order_probability=0.50,
                cancel_probability=0.20,
                modify_probability=0.20
            )

    def test_rejects_probability_outside_valid_range(self) -> None:
        with self.assertRaises(ValueError):
            SimulationConfig(buy_probability=1.1)

        with self.assertRaises(ValueError):
            SimulationConfig(market_order_probability=-0.1)


if __name__ == "__main__":
    unittest.main()
