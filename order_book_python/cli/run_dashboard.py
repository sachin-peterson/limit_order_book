from __future__ import annotations

import argparse

from order_book_python.engine.types.instruments import Instrument
from order_book_python.simulation.clock import SimulationClock
from order_book_python.simulation.config import SimulationConfig

from .dashboard import run_dashboard


def create_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run the order-book terminal dashboard"
    )

    parser.add_argument(
        "--symbol",
        type=str,
        default="TEST",
        help="Instrument symbol"
    )
    parser.add_argument(
        "--tick-size",
        type=int,
        default=1,
        help="Minimum price increment"
    )
    parser.add_argument(
        "--lot-size",
        type=int,
        default=1,
        help="Minimum order-size increment"
    )
    parser.add_argument(
        "--actions",
        type=int,
        default=1_000,
        help="Number of generated requests"
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Random seed"
    )
    parser.add_argument(
        "--initial-price",
        type=int,
        default=10_000,
        help="Reference price when the book is empty"
    )
    parser.add_argument(
        "--clients",
        type=int,
        default=100,
        help="Number of simulated clients"
    )
    parser.add_argument(
        "--min-lots",
        type=int,
        default=1,
        help="Minimum generated size in lots"
    )
    parser.add_argument(
        "--max-lots",
        type=int,
        default=100,
        help="Maximum generated size in lots"
    )
    parser.add_argument(
        "--price-range",
        type=int,
        default=20,
        help="Maximum price distance in ticks"
    )
    parser.add_argument(
        "--new-order-probability",
        type=float,
        default=0.75,
        help="Probability of a new order"
    )
    parser.add_argument(
        "--cancel-probability",
        type=float,
        default=0.15,
        help="Probability of a cancellation"
    )
    parser.add_argument(
        "--modify-probability",
        type=float,
        default=0.10,
        help="Probability of a modification"
    )
    parser.add_argument(
        "--buy-probability",
        type=float,
        default=0.50,
        help="Probability that a new order is a buy"
    )
    parser.add_argument(
        "--market-order-probability",
        type=float,
        default=0.10,
        help="Probability that a new order is a market order"
    )
    parser.add_argument(
        "--clock-start",
        type=int,
        default=0,
        help="First simulated timestamp"
    )
    parser.add_argument(
        "--clock-step",
        type=int,
        default=1,
        help="Simulated timestamp increment"
    )
    parser.add_argument(
        "--request-delay",
        type=float,
        default=1.0,
        help="Seconds between generated requests"
    )
    parser.add_argument(
        "--depth",
        type=int,
        default=10,
        help="Number of price levels displayed per side"
    )
    parser.add_argument(
        "--validate",
        action="store_true",
        help="Validate state after every request"
    )

    return parser


def main() -> None:
    parser = create_argument_parser()
    arguments = parser.parse_args()

    try:
        instrument = Instrument(
            symbol=arguments.symbol,
            tick_size=arguments.tick_size,
            lot_size=arguments.lot_size
        )

        config = SimulationConfig(
            action_count=arguments.actions,
            seed=arguments.seed,
            initial_price=arguments.initial_price,
            client_count=arguments.clients,
            min_lot_count=arguments.min_lots,
            max_lot_count=arguments.max_lots,
            price_range_ticks=arguments.price_range,
            new_order_probability=arguments.new_order_probability,
            cancel_probability=arguments.cancel_probability,
            modify_probability=arguments.modify_probability,
            buy_probability=arguments.buy_probability,
            market_order_probability=arguments.market_order_probability
        )

        clock = SimulationClock(
            start=arguments.clock_start,
            step=arguments.clock_step
        )

        run_dashboard(
            instrument=instrument,
            config=config,
            clock=clock,
            validate=arguments.validate,
            request_delay=arguments.request_delay,
            depth=arguments.depth
        )

    except ValueError as error:
        parser.error(str(error))


if __name__ == "__main__":
    main()
