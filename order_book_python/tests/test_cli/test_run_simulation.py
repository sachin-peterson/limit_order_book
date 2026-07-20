import sys
import unittest
from contextlib import redirect_stdout
from io import StringIO
from unittest.mock import Mock, patch

from order_book_python.cli.run_simulation import (
    create_argument_parser,
    create_event_printer,
    main
)
from order_book_python.engine.types.enums import EventType
from order_book_python.engine.types.events import Event


class TestRunSimulation(unittest.TestCase):
    def test_argument_parser_defaults(self) -> None:
        parser = create_argument_parser()
        arguments = parser.parse_args([])

        self.assertEqual(arguments.symbol, "TEST")
        self.assertEqual(arguments.tick_size, 1)
        self.assertEqual(arguments.lot_size, 1)
        self.assertEqual(arguments.actions, 1_000)
        self.assertIsNone(arguments.seed)
        self.assertEqual(arguments.event_delay, 0.0)
        self.assertFalse(arguments.validate)
        self.assertFalse(arguments.quiet)

    def test_event_printer_rejects_negative_delay(self) -> None:
        with self.assertRaises(ValueError):
            create_event_printer(-1)

    def test_event_printer_prints_event(self) -> None:
        event = Event(
            sequence=3,
            timestamp=10,
            event_type=EventType.ORDER_ACCEPTED,
            details={"order_id": 7}
        )

        output = StringIO()
        printer = create_event_printer(0)

        with redirect_stdout(output):
            printer(event)

        text = output.getvalue()

        self.assertIn("[10]", text)
        self.assertIn("#3", text)
        self.assertIn(EventType.ORDER_ACCEPTED.value, text)
        self.assertIn('"order_id": 7', text)

    def test_event_printer_uses_configured_delay(self) -> None:
        event = Event(
            sequence=1,
            timestamp=0,
            event_type=EventType.ORDER_ACCEPTED,
            details={}
        )

        printer = create_event_printer(0.5)

        with (
            patch(
                "order_book_python.cli.run_simulation.time.sleep"
            ) as sleep,
            redirect_stdout(StringIO())
        ):
            printer(event)

        sleep.assert_called_once_with(0.5)

    def test_event_printer_does_not_sleep_for_zero_delay(
        self
    ) -> None:
        event = Event(
            sequence=1,
            timestamp=0,
            event_type=EventType.ORDER_ACCEPTED,
            details={}
        )

        printer = create_event_printer(0)

        with (
            patch(
                "order_book_python.cli.run_simulation.time.sleep"
            ) as sleep,
            redirect_stdout(StringIO())
        ):
            printer(event)

        sleep.assert_not_called()

    def test_main_runs_quiet_simulation(self) -> None:
        book = Mock()
        book.get_book_snapshot.return_value = {
            "symbol": "TEST"
        }

        with (
            patch.object(
                sys,
                "argv",
                [
                    "run_simulation",
                    "--actions",
                    "10",
                    "--seed",
                    "42",
                    "--quiet",
                    "--validate"
                ]
            ),
            patch(
                "order_book_python.cli.run_simulation.SimulationRunner"
            ) as runner_class,
            redirect_stdout(StringIO())
        ):
            runner = runner_class.return_value
            runner.run.return_value = book

            main()

        runner_class.assert_called_once()

        runner_arguments = runner_class.call_args.kwargs

        self.assertTrue(
            runner_arguments["validate_after_each_request"]
        )

        run_arguments = runner.run.call_args.kwargs

        self.assertEqual(
            run_arguments["config"].action_count,
            10
        )
        self.assertEqual(
            run_arguments["config"].seed,
            42
        )
        self.assertIsNone(run_arguments["on_event"])

        book.get_book_snapshot.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
