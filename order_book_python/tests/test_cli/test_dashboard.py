import threading
import unittest
from queue import Empty, Queue
from unittest.mock import Mock, call

from order_book_python.cli.dashboard import (
    create_snapshot,
    format_event,
    get_levels,
    replace_snapshot,
    run_dashboard,
    run_simulation_worker
)
from order_book_python.engine.types.enums import EventType, Side
from order_book_python.engine.types.events import Event
from order_book_python.engine.types.instruments import Instrument
from order_book_python.simulation.clock import SimulationClock
from order_book_python.simulation.config import SimulationConfig


class TestDashboard(unittest.TestCase):
    def test_format_event(self) -> None:
        event = Event(
            sequence=5,
            timestamp=20,
            event_type=EventType.ORDER_RESTED,
            details={
                "size": 10,
                "order_id": 3
            }
        )

        result = format_event(event)

        self.assertEqual(
            result,
            (
                f"[20] #5 "
                f"{EventType.ORDER_RESTED.value} "
                '{"order_id": 3, "size": 10}'
            )
        )

    def test_create_snapshot_requests_both_sides(
        self
    ) -> None:
        order_book = Mock()

        order_book.get_book_snapshot.return_value = {
            "symbol": "TEST"
        }

        order_book.get_side_snapshot.side_effect = [
            {"side": "BUY"},
            {"side": "SELL"}
        ]

        snapshot = create_snapshot(
            order_book,
            depth=5
        )

        self.assertEqual(
            snapshot["book"],
            {"symbol": "TEST"}
        )
        self.assertEqual(
            snapshot["bids"],
            {"side": "BUY"}
        )
        self.assertEqual(
            snapshot["asks"],
            {"side": "SELL"}
        )

        order_book.get_side_snapshot.assert_has_calls([
            call(
                side=Side.BUY,
                depth=5
            ),
            call(
                side=Side.SELL,
                depth=5
            )
        ])

    def test_replace_snapshot_adds_to_empty_queue(
        self
    ) -> None:
        snapshot_queue: Queue[dict[str, object]] = Queue(
            maxsize=1
        )

        snapshot = {"book": {"event_count": 1}}

        replace_snapshot(
            snapshot_queue,
            snapshot
        )

        self.assertEqual(
            snapshot_queue.get_nowait(),
            snapshot
        )

    def test_replace_snapshot_replaces_old_value(
        self
    ) -> None:
        snapshot_queue: Queue[dict[str, object]] = Queue(
            maxsize=1
        )

        old_snapshot = {
            "book": {
                "event_count": 1
            }
        }

        new_snapshot = {
            "book": {
                "event_count": 2
            }
        }

        snapshot_queue.put_nowait(old_snapshot)

        replace_snapshot(
            snapshot_queue,
            new_snapshot
        )

        self.assertEqual(
            snapshot_queue.get_nowait(),
            new_snapshot
        )

        with self.assertRaises(Empty):
            snapshot_queue.get_nowait()

    def test_get_levels_returns_dictionary_levels(
        self
    ) -> None:
        snapshot = {
            "levels": [
                {
                    "price": 100,
                    "total_size": 10
                },
                "invalid",
                {
                    "price": 99,
                    "total_size": 20
                }
            ]
        }

        levels = get_levels(snapshot)

        self.assertEqual(
            levels,
            [
                {
                    "price": 100,
                    "total_size": 10
                },
                {
                    "price": 99,
                    "total_size": 20
                }
            ]
        )

    def test_get_levels_handles_invalid_snapshot(
        self
    ) -> None:
        self.assertEqual(get_levels(None), [])
        self.assertEqual(get_levels({}), [])
        self.assertEqual(
            get_levels({"levels": "invalid"}),
            []
        )

    def test_worker_runs_simulation_and_completes(
        self
    ) -> None:
        instrument = Instrument(
            symbol="TEST",
            tick_size=1,
            lot_size=1
        )

        config = SimulationConfig(
            action_count=10,
            seed=42
        )

        event_queue: Queue[str] = Queue()

        snapshot_queue: Queue[
            dict[str, object]
        ] = Queue(maxsize=1)

        error_queue: Queue[BaseException] = Queue()

        stop_event = threading.Event()
        pause_event = threading.Event()
        completed_event = threading.Event()

        run_simulation_worker(
            instrument=instrument,
            config=config,
            clock=SimulationClock(),
            validate=True,
            depth=5,
            request_delay=0,
            event_queue=event_queue,
            snapshot_queue=snapshot_queue,
            stop_event=stop_event,
            pause_event=pause_event,
            completed_event=completed_event,
            error_queue=error_queue
        )

        self.assertTrue(completed_event.is_set())
        self.assertFalse(event_queue.empty())
        self.assertFalse(snapshot_queue.empty())
        self.assertTrue(error_queue.empty())

        snapshot = snapshot_queue.get_nowait()

        self.assertIn("book", snapshot)
        self.assertIn("bids", snapshot)
        self.assertIn("asks", snapshot)

    def test_run_dashboard_rejects_negative_delay(
        self
    ) -> None:
        instrument = Instrument("TEST")

        with self.assertRaises(ValueError):
            run_dashboard(
                instrument=instrument,
                config=SimulationConfig(
                    action_count=1,
                    seed=42
                ),
                clock=SimulationClock(),
                validate=False,
                request_delay=-1,
                depth=5
            )

    def test_run_dashboard_rejects_invalid_depth(
        self
    ) -> None:
        instrument = Instrument("TEST")

        with self.assertRaises(ValueError):
            run_dashboard(
                instrument=instrument,
                config=SimulationConfig(
                    action_count=1,
                    seed=42
                ),
                clock=SimulationClock(),
                validate=False,
                request_delay=0,
                depth=0
            )


if __name__ == "__main__":
    unittest.main()
