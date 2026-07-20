from __future__ import annotations

import curses
import json
import threading
import time
from queue import Empty, Full, Queue

from order_book_python.engine.matching_engine import OrderBook
from order_book_python.engine.types.enums import Side
from order_book_python.engine.types.events import Event
from order_book_python.engine.types.instruments import Instrument
from order_book_python.simulation.clock import SimulationClock
from order_book_python.simulation.config import SimulationConfig
from order_book_python.simulation.runner import SimulationRunner


class SimulationStopped(Exception):
    pass


def format_event(event: Event) -> str:
    details = json.dumps(
        event.details,
        sort_keys=True
    )

    return (
        f"[{event.timestamp}] "
        f"#{event.sequence} "
        f"{event.event_type.value} "
        f"{details}"
    )


def create_snapshot(
    order_book: OrderBook,
    depth: int
) -> dict[str, object]:
    return {
        "book": order_book.get_book_snapshot(),
        "bids": order_book.get_side_snapshot(
            side=Side.BUY,
            depth=depth
        ),
        "asks": order_book.get_side_snapshot(
            side=Side.SELL,
            depth=depth
        )
    }


def replace_snapshot(
    snapshot_queue: Queue[dict[str, object]],
    snapshot: dict[str, object]
) -> None:
    try:
        snapshot_queue.put_nowait(snapshot)
        return
    except Full:
        pass

    try:
        snapshot_queue.get_nowait()
    except Empty:
        pass

    snapshot_queue.put_nowait(snapshot)


def run_simulation_worker(
    instrument: Instrument,
    config: SimulationConfig,
    clock: SimulationClock,
    validate: bool,
    depth: int,
    request_delay: float,
    event_queue: Queue[str],
    snapshot_queue: Queue[dict[str, object]],
    stop_event: threading.Event,
    pause_event: threading.Event,
    completed_event: threading.Event,
    error_queue: Queue[BaseException]
) -> None:
    processed_steps = 0

    def handle_event(event: Event) -> None:
        event_queue.put(format_event(event))

    def handle_step(order_book: OrderBook) -> None:
        nonlocal processed_steps

        if stop_event.is_set():
            raise SimulationStopped

        replace_snapshot(
            snapshot_queue,
            create_snapshot(order_book, depth)
        )

        final_callback = processed_steps >= config.action_count

        if final_callback:
            return

        processed_steps += 1

        while pause_event.is_set():
            if stop_event.is_set():
                raise SimulationStopped

            time.sleep(0.05)

        if request_delay <= 0:
            return

        delay_end = time.monotonic() + request_delay

        while time.monotonic() < delay_end:
            if stop_event.is_set():
                raise SimulationStopped

            while pause_event.is_set():
                if stop_event.is_set():
                    raise SimulationStopped

                time.sleep(0.05)

                delay_end = time.monotonic() + request_delay

            remaining = delay_end - time.monotonic()

            if remaining > 0:
                time.sleep(min(remaining, 0.05))

    try:
        runner = SimulationRunner(
            validate_after_each_request=validate,
            clock=clock
        )

        runner.run(
            instrument=instrument,
            config=config,
            on_event=handle_event,
            on_step=handle_step
        )

    except SimulationStopped:
        pass

    except BaseException as error:
        error_queue.put(error)

    finally:
        completed_event.set()


def safe_add_text(
    screen: curses.window,
    row: int,
    column: int,
    text: str,
    attributes: int = 0
) -> None:
    height, width = screen.getmaxyx()

    if row < 0 or row >= height:
        return

    if column < 0 or column >= width:
        return

    available_width = width - column - 1

    if available_width <= 0:
        return

    try:
        screen.addnstr(
            row,
            column,
            text,
            available_width,
            attributes
        )
    except curses.error:
        pass


def get_levels(
    side_snapshot: object
) -> list[dict[str, object]]:
    if not isinstance(side_snapshot, dict):
        return []

    levels = side_snapshot.get("levels")

    if not isinstance(levels, list):
        return []

    return [
        level
        for level in levels
        if isinstance(level, dict)
    ]


def draw_event_panel(
    screen: curses.window,
    events: list[str],
    divider_column: int
) -> None:
    height, _ = screen.getmaxyx()

    safe_add_text(
        screen,
        1,
        2,
        "EVENT STREAM",
        curses.A_BOLD
    )

    available_rows = height - 5
    visible_events = events[-available_rows:]

    for index, event in enumerate(visible_events):
        safe_add_text(
            screen,
            index + 3,
            1,
            event[:divider_column - 2]
        )


def draw_book_panel(
    screen: curses.window,
    snapshot: dict[str, object] | None,
    divider_column: int
) -> None:
    _, width = screen.getmaxyx()
    column = divider_column + 2
    panel_width = width - column - 1

    safe_add_text(
        screen,
        1,
        column,
        "ORDER BOOK",
        curses.A_BOLD
    )

    if snapshot is None:
        safe_add_text(
            screen,
            3,
            column,
            "Waiting for first snapshot..."
        )
        return

    book = snapshot.get("book")

    if not isinstance(book, dict):
        return

    metric_lines = [
        f"Symbol:        {book.get('symbol')}",
        f"Best bid:      {book.get('best_bid')}",
        f"Best ask:      {book.get('best_ask')}",
        f"Spread:        {book.get('spread')}",
        f"Mid price:     {book.get('mid_price')}",
        f"Active orders: {book.get('active_orders')}",
        f"Trades:        {book.get('trade_count')}",
        f"Events:        {book.get('event_count')}"
    ]

    for index, line in enumerate(metric_lines):
        safe_add_text(
            screen,
            index + 3,
            column,
            line
        )

    bid_levels = get_levels(snapshot.get("bids"))
    ask_levels = get_levels(snapshot.get("asks"))

    table_row = 12

    safe_add_text(
        screen,
        table_row,
        column,
        "MARKET DEPTH",
        curses.A_BOLD
    )

    header = (
        f"{'BID':>8} {'SIZE':>6} | "
        f"{'ASK':>8} {'SIZE':>6}"
    )

    safe_add_text(
        screen,
        table_row + 1,
        column,
        header[:panel_width]
    )

    level_count = max(
        len(bid_levels),
        len(ask_levels)
    )

    for index in range(level_count):
        bid_price: object = ""
        bid_size: object = ""
        ask_price: object = ""
        ask_size: object = ""

        if index < len(bid_levels):
            bid_price = bid_levels[index].get("price", "")
            bid_size = bid_levels[index].get("total_size", "")

        if index < len(ask_levels):
            ask_price = ask_levels[index].get("price", "")
            ask_size = ask_levels[index].get("total_size", "")

        row = (
            f"{str(bid_price):>8} "
            f"{str(bid_size):>6} | "
            f"{str(ask_price):>8} "
            f"{str(ask_size):>6}"
        )

        safe_add_text(
            screen,
            table_row + index + 2,
            column,
            row[:panel_width]
        )


def draw_dashboard(
    screen: curses.window,
    events: list[str],
    snapshot: dict[str, object] | None,
    paused: bool,
    completed: bool,
    validate: bool,
    error: BaseException | None
) -> None:
    screen.erase()

    height, width = screen.getmaxyx()

    if height < 20 or width < 90:
        safe_add_text(
            screen,
            0,
            0,
            "Terminal must be at least 90 columns by 20 rows."
        )
        screen.refresh()
        return

    divider_column = int(width * 0.62)

    safe_add_text(
        screen,
        0,
        2,
        "ORDER BOOK SIMULATION",
        curses.A_BOLD
    )

    try:
        screen.hline(
            2,
            0,
            curses.ACS_HLINE,
            width
        )

        screen.hline(
            height - 2,
            0,
            curses.ACS_HLINE,
            width
        )

        screen.vline(
            1,
            divider_column,
            curses.ACS_VLINE,
            height - 3
        )
    except curses.error:
        pass

    draw_event_panel(
        screen,
        events,
        divider_column
    )

    draw_book_panel(
        screen,
        snapshot,
        divider_column
    )

    if error is not None:
        status = f"ERROR: {error}"
    elif completed:
        status = "COMPLETE"
    elif paused:
        status = "PAUSED"
    else:
        status = "RUNNING"

    validation_status = "ON" if validate else "OFF"

    footer = (
        f"[P] pause/resume  [C] clear events  [Q] quit"
        f"    Status: {status}"
        f"    Validation: {validation_status}"
    )

    safe_add_text(
        screen,
        height - 1,
        1,
        footer
    )

    screen.refresh()


def dashboard_loop(
    screen: curses.window,
    event_queue: Queue[str],
    snapshot_queue: Queue[dict[str, object]],
    stop_event: threading.Event,
    pause_event: threading.Event,
    completed_event: threading.Event,
    error_queue: Queue[BaseException],
    validate: bool
) -> None:
    try:
        curses.curs_set(0)
    except curses.error:
        pass

    screen.nodelay(True)
    screen.timeout(50)

    events: list[str] = []
    snapshot: dict[str, object] | None = None
    worker_error: BaseException | None = None

    while True:
        while True:
            try:
                events.append(event_queue.get_nowait())
            except Empty:
                break

        if len(events) > 2_000:
            events = events[-2_000:]

        while True:
            try:
                snapshot = snapshot_queue.get_nowait()
            except Empty:
                break

        if worker_error is None:
            try:
                worker_error = error_queue.get_nowait()
            except Empty:
                pass

        key = screen.getch()

        if key in {ord("q"), ord("Q")}:
            stop_event.set()
            return

        if key in {ord("p"), ord("P")}:
            if pause_event.is_set():
                pause_event.clear()
            else:
                pause_event.set()

        if key in {ord("c"), ord("C")}:
            events.clear()

        draw_dashboard(
            screen=screen,
            events=events,
            snapshot=snapshot,
            paused=pause_event.is_set(),
            completed=completed_event.is_set(),
            validate=validate,
            error=worker_error
        )


def run_dashboard(
    instrument: Instrument,
    config: SimulationConfig,
    clock: SimulationClock,
    validate: bool,
    request_delay: float,
    depth: int
) -> None:
    if request_delay < 0:
        raise ValueError("Request delay cannot be negative")

    if not isinstance(depth, int) or depth <= 0:
        raise ValueError("Depth must be a positive integer")

    event_queue: Queue[str] = Queue()
    snapshot_queue: Queue[dict[str, object]] = Queue(
        maxsize=1
    )
    error_queue: Queue[BaseException] = Queue()

    stop_event = threading.Event()
    pause_event = threading.Event()
    completed_event = threading.Event()

    worker = threading.Thread(
        target=run_simulation_worker,
        args=(
            instrument,
            config,
            clock,
            validate,
            depth,
            request_delay,
            event_queue,
            snapshot_queue,
            stop_event,
            pause_event,
            completed_event,
            error_queue
        ),
        daemon=True
    )

    worker.start()

    try:
        curses.wrapper(
            dashboard_loop,
            event_queue,
            snapshot_queue,
            stop_event,
            pause_event,
            completed_event,
            error_queue,
            validate
        )
    finally:
        stop_event.set()
        pause_event.clear()
        worker.join(timeout=1)
