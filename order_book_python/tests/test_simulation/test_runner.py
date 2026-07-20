import unittest

from order_book_python.engine.types.enums import EventType
from order_book_python.engine.types.events import Event
from order_book_python.engine.types.instruments import Instrument
from order_book_python.simulation.clock import SimulationClock
from order_book_python.simulation.config import SimulationConfig
from order_book_python.simulation.runner import SimulationRunner

from .helpers import create_instrument, event_signature


class TestSimulationRunner(unittest.TestCase):
    def test_runner_processes_configured_action_count(self) -> None:
        config = SimulationConfig(
            action_count=20,
            seed=42,
            new_order_probability=1.0,
            cancel_probability=0.0,
            modify_probability=0.0,
            market_order_probability=0.0
        )

        runner = SimulationRunner(clock=SimulationClock())
        book = runner.run(instrument=create_instrument(), config=config)

        accepted_events = [
            event
            for event in book.events
            if event.event_type is EventType.ORDER_ACCEPTED
        ]

        self.assertEqual(len(accepted_events), 20)

    def test_runner_streams_all_generated_events(self) -> None:
        config = SimulationConfig(
            action_count=20,
            seed=42
        )

        streamed_events: list[Event] = []

        runner = SimulationRunner(clock=SimulationClock())

        book = runner.run(
            instrument=create_instrument(),
            config=config,
            on_event=streamed_events.append
        )

        self.assertEqual(streamed_events, book.events)

    def test_same_seed_and_clock_produce_same_events(self) -> None:
        config = SimulationConfig(
            action_count=100,
            seed=42
        )

        first_runner = SimulationRunner(
            clock=SimulationClock(
                start=1_000,
                step=10
            )
        )

        second_runner = SimulationRunner(
            clock=SimulationClock(
                start=1_000,
                step=10
            )
        )

        first_book = first_runner.run(
            instrument=create_instrument(),
            config=config
        )

        second_book = second_runner.run(
            instrument=create_instrument(),
            config=config
        )

        first_events = [
            event_signature(event)
            for event in first_book.events
        ]

        second_events = [
            event_signature(event)
            for event in second_book.events
        ]

        self.assertEqual(first_events, second_events)

    def test_deterministic_event_timestamps_are_ordered(self) -> None:
        runner = SimulationRunner(
            clock=SimulationClock(
                start=100,
                step=5
            )
        )

        book = runner.run(
            instrument=create_instrument(),
            config=SimulationConfig(
                action_count=20,
                seed=42
            )
        )

        timestamps = [
            event.timestamp
            for event in book.events
        ]

        self.assertEqual(
            timestamps,
            sorted(timestamps)
        )

        self.assertEqual(
            len(timestamps),
            len(set(timestamps))
        )

    def test_runner_can_validate_after_every_request(self) -> None:
        runner = SimulationRunner(
            validate_after_each_request=True,
            clock=SimulationClock()
        )

        book = runner.run(
            instrument=create_instrument(),
            config=SimulationConfig(
                action_count=100,
                seed=42
            )
        )

        self.assertGreater(len(book.events), 0)


if __name__ == "__main__":
    unittest.main()
