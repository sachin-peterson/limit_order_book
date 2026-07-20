import sys
import unittest
from unittest.mock import patch

from order_book_python.cli.run_dashboard import (
    create_argument_parser,
    main
)


class TestRunDashboard(unittest.TestCase):
    def test_argument_parser_defaults(self) -> None:
        parser = create_argument_parser()
        arguments = parser.parse_args([])

        self.assertEqual(arguments.symbol, "TEST")
        self.assertEqual(arguments.tick_size, 1)
        self.assertEqual(arguments.lot_size, 1)
        self.assertEqual(arguments.actions, 1_000)
        self.assertIsNone(arguments.seed)
        self.assertEqual(arguments.request_delay, 1.0)
        self.assertEqual(arguments.depth, 10)
        self.assertFalse(arguments.validate)

    def test_main_starts_dashboard_with_arguments(
        self
    ) -> None:
        with (
            patch.object(
                sys,
                "argv",
                [
                    "run_dashboard",
                    "--symbol",
                    "ABC",
                    "--tick-size",
                    "5",
                    "--lot-size",
                    "10",
                    "--actions",
                    "25",
                    "--seed",
                    "42",
                    "--request-delay",
                    "0.5",
                    "--depth",
                    "8",
                    "--validate"
                ]
            ),
            patch(
                "order_book_python.cli.run_dashboard.run_dashboard"
            ) as dashboard
        ):
            main()

        dashboard.assert_called_once()

        arguments = dashboard.call_args.kwargs

        self.assertEqual(
            arguments["instrument"].symbol,
            "ABC"
        )
        self.assertEqual(
            arguments["instrument"].tick_size,
            5
        )
        self.assertEqual(
            arguments["instrument"].lot_size,
            10
        )

        self.assertEqual(
            arguments["config"].action_count,
            25
        )
        self.assertEqual(
            arguments["config"].seed,
            42
        )

        self.assertEqual(
            arguments["request_delay"],
            0.5
        )
        self.assertEqual(
            arguments["depth"],
            8
        )
        self.assertTrue(arguments["validate"])


if __name__ == "__main__":
    unittest.main()
