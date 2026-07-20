from __future__ import annotations

import curses
import json
import textwrap
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
    """Returns the original full event representation."""
    details = json.dumps(event.details, sort_keys=True)

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
    event_queue: Queue[Event],
    snapshot_queue: Queue[dict[str, object]],
    stop_event: threading.Event,
    pause_event: threading.Event,
    completed_event: threading.Event,
    error_queue: Queue[BaseException]
) -> None:
    processed_steps = 0

    def handle_event(event: Event) -> None:
        event_queue.put(event)

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
    attributes: int = 0,
    max_width: int | None = None
) -> None:
    height, width = screen.getmaxyx()

    if row < 0 or row >= height:
        return

    if column < 0 or column >= width:
        return

    available_width = width - column - 1
    if max_width is not None:
        available_width = min(available_width, max_width)

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


def truncate(text: str, width: int) -> str:
    if width <= 0:
        return ""

    if len(text) <= width:
        return text

    if width <= 3:
        return text[:width]

    return text[:width - 3] + "..."


def display_value(value: object) -> str:
    if value is None or value == "":
        return "-"

    return str(value)


def get_event_value(
    event: Event,
    *keys: str
) -> str:
    for key in keys:
        if key in event.details:
            return display_value(event.details[key])

    return "-"


def get_event_columns(event: Event) -> dict[str, str]:
    event_type = event.event_type.value

    order_id = get_event_value(
        event,
        "order_id",
        "taker_order_id"
    )
    client_id = get_event_value(
        event,
        "client_id",
        "taker_client_id"
    )
    side = get_event_value(
        event,
        "side",
        "taker_side"
    )
    price = get_event_value(
        event,
        "trade_price",
        "new_price",
        "price"
    )
    size = get_event_value(
        event,
        "trade_size",
        "cancelled_size",
        "new_size",
        "original_size",
        "size"
    )
    remaining = get_event_value(
        event,
        "remaining_size"
    )

    return {
        "timestamp": str(event.timestamp),
        "sequence": str(event.sequence),
        "event_type": event_type,
        "order_id": order_id,
        "client_id": client_id,
        "side": side,
        "price": price,
        "size": size,
        "remaining": remaining
    }


def get_event_header(width: int) -> str:
    if width >= 104:
        return (
            f"{'TIME':>6} "
            f"{'SEQ':>5} "
            f"{'EVENT':<25} "
            f"{'ORDER':>6} "
            f"{'CLIENT':>6} "
            f"{'SIDE':<4} "
            f"{'PRICE':>8} "
            f"{'SIZE':>6} "
            f"{'REM':>6}"
        )

    if width >= 82:
        return (
            f"{'SEQ':>5} "
            f"{'EVENT':<25} "
            f"{'ORDER':>6} "
            f"{'SIDE':<4} "
            f"{'PRICE':>8} "
            f"{'SIZE':>6} "
            f"{'REM':>6}"
        )

    if width >= 64:
        return (
            f"{'SEQ':>5} "
            f"{'EVENT':<25} "
            f"{'ORDER':>6} "
            f"{'PRICE':>8} "
            f"{'SIZE':>6}"
        )

    return f"{'SEQ':>5} {'EVENT':<25}"


def format_event_row(event: Event, width: int) -> str:
    columns = get_event_columns(event)

    if width >= 104:
        row = (
            f"{columns['timestamp']:>6.6} "
            f"{columns['sequence']:>5.5} "
            f"{columns['event_type']:<25.25} "
            f"{columns['order_id']:>6.6} "
            f"{columns['client_id']:>6.6} "
            f"{columns['side']:<4.4} "
            f"{columns['price']:>8.8} "
            f"{columns['size']:>6.6} "
            f"{columns['remaining']:>6.6}"
        )
    elif width >= 82:
        row = (
            f"{columns['sequence']:>5.5} "
            f"{columns['event_type']:<25.25} "
            f"{columns['order_id']:>6.6} "
            f"{columns['side']:<4.4} "
            f"{columns['price']:>8.8} "
            f"{columns['size']:>6.6} "
            f"{columns['remaining']:>6.6}"
        )
    elif width >= 64:
        row = (
            f"{columns['sequence']:>5.5} "
            f"{columns['event_type']:<25.25} "
            f"{columns['order_id']:>6.6} "
            f"{columns['price']:>8.8} "
            f"{columns['size']:>6.6}"
        )
    else:
        row = (
            f"{columns['sequence']:>5.5} "
            f"{columns['event_type']:<25.25}"
        )

    return truncate(row, width)


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


def get_selected_event(
    events: list[Event],
    selected_index: int | None
) -> Event | None:
    if not events:
        return None

    if selected_index is None:
        return events[-1]

    index = max(0, min(selected_index, len(events) - 1))
    return events[index]


def get_visible_event_range(
    event_count: int,
    available_rows: int,
    selected_index: int | None
) -> range:
    if event_count == 0 or available_rows <= 0:
        return range(0)

    if selected_index is None:
        start = max(0, event_count - available_rows)
        return range(start, event_count)

    selected_index = max(0, min(selected_index, event_count - 1))
    half_window = available_rows // 2
    start = max(0, selected_index - half_window)
    end = min(event_count, start + available_rows)
    start = max(0, end - available_rows)

    return range(start, end)


def draw_event_panel(
    screen: curses.window,
    events: list[Event],
    selected_index: int | None,
    divider_column: int
) -> None:
    height, _ = screen.getmaxyx()
    panel_width = divider_column - 2
    table_width = max(1, panel_width - 1)

    follow_status = "LIVE" if selected_index is None else "BROWSING"
    title = f"EVENT STREAM  {follow_status}  {len(events)} EVENTS"

    safe_add_text(
        screen,
        1,
        2,
        title,
        curses.A_BOLD,
        panel_width
    )
    safe_add_text(
        screen,
        3,
        2,
        get_event_header(table_width),
        curses.A_BOLD,
        panel_width
    )

    available_rows = height - 7
    visible_range = get_visible_event_range(
        len(events),
        available_rows,
        selected_index
    )

    selected_position = (
        len(events) - 1
        if selected_index is None and events
        else selected_index
    )

    for row_offset, event_index in enumerate(visible_range):
        event = events[event_index]
        is_selected = event_index == selected_position
        marker = ">" if is_selected else " "
        attributes = curses.A_REVERSE if is_selected else 0
        row = marker + format_event_row(event, table_width)

        safe_add_text(
            screen,
            row_offset + 4,
            1,
            row,
            attributes,
            divider_column - 1
        )


def format_detail_value(value: object) -> str:
    if isinstance(value, (dict, list)):
        return json.dumps(value, sort_keys=True)

    return display_value(value)


def format_detail_label(key: str) -> str:
    return key.replace("_", " ").title()


def wrap_detail(
    label: str,
    value: str,
    width: int
) -> list[str]:
    prefix = f"{label}: "
    value_width = max(1, width - len(prefix))
    wrapped_value = textwrap.wrap(
        value,
        width=value_width,
        break_long_words=True,
        break_on_hyphens=False
    )

    if not wrapped_value:
        return [prefix.rstrip()]

    lines = [prefix + wrapped_value[0]]
    indent = " " * len(prefix)
    lines.extend(indent + line for line in wrapped_value[1:])
    return lines


def get_selected_event_lines(
    event: Event,
    width: int
) -> list[str]:
    lines = [
        f"#{event.sequence} {event.event_type.value}"
    ]
    lines.extend(
        wrap_detail(
            "Timestamp",
            str(event.timestamp),
            width
        )
    )

    for key in sorted(event.details):
        lines.extend(
            wrap_detail(
                format_detail_label(key),
                format_detail_value(event.details[key]),
                width
            )
        )

    return lines


def draw_book_panel(
    screen: curses.window,
    snapshot: dict[str, object] | None,
    selected_event: Event | None,
    divider_column: int
) -> None:
    height, width = screen.getmaxyx()
    column = divider_column + 2
    panel_width = width - column - 1
    content_bottom = height - 3

    safe_add_text(
        screen,
        1,
        column,
        "ORDER BOOK",
        curses.A_BOLD,
        panel_width
    )

    if snapshot is None:
        safe_add_text(
            screen,
            3,
            column,
            "Waiting for first snapshot...",
            0,
            panel_width
        )
        return

    book = snapshot.get("book")
    if not isinstance(book, dict):
        return

    metric_lines = [
        f"{'Symbol:':<15}{display_value(book.get('symbol'))}",
        f"{'Best bid:':<15}{display_value(book.get('best_bid'))}",
        f"{'Best ask:':<15}{display_value(book.get('best_ask'))}",
        f"{'Mid price:':<15}{display_value(book.get('mid_price'))}",
        f"{'Spread:':<15}{display_value(book.get('spread'))}",
        f"{'Active orders:':<15}{display_value(book.get('active_orders'))}",
        f"{'Trades:':<15}{display_value(book.get('trade_count'))}",
        f"{'Events:':<15}{display_value(book.get('event_count'))}"
    ]

    for index, line in enumerate(metric_lines):
        safe_add_text(
            screen,
            index + 3,
            column,
            line,
            0,
            panel_width
        )

    bid_levels = get_levels(snapshot.get("bids"))
    ask_levels = get_levels(snapshot.get("asks"))

    table_row = 12
    safe_add_text(
        screen,
        table_row,
        column,
        "MARKET DEPTH",
        curses.A_BOLD,
        panel_width
    )

    header = (
        f"{'BID':<8} "
        f"{'SIZE':>6} | "
        f"{'ASK':<8} "
        f"{'SIZE':>6}"
    )
    safe_add_text(
        screen,
        table_row + 1,
        column,
        header,
        curses.A_BOLD,
        panel_width
    )

    selected_reserved_rows = 16 if selected_event is not None else 5
    available_depth_rows = max(
        1,
        content_bottom
        - (table_row + 2)
        - selected_reserved_rows
        - 1
    )
    level_count = min(
        max(len(bid_levels), len(ask_levels)),
        available_depth_rows
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
            f"{str(bid_price):<8} "
            f"{str(bid_size):>6} | "
            f"{str(ask_price):<8} "
            f"{str(ask_size):>6}"
        )
        safe_add_text(
            screen,
            table_row + index + 2,
            column,
            row,
            0,
            panel_width
        )

    selected_row = table_row + level_count + 3
    safe_add_text(
        screen,
        selected_row,
        column,
        "SELECTED EVENT",
        curses.A_BOLD,
        panel_width
    )

    if selected_event is None:
        safe_add_text(
            screen,
            selected_row + 2,
            column,
            "Waiting for first event...",
            0,
            panel_width
        )
        return

    detail_lines = get_selected_event_lines(
        selected_event,
        panel_width
    )
    available_detail_rows = max(
        0,
        content_bottom - selected_row - 1
    )

    if len(detail_lines) > available_detail_rows:
        hidden_line_count = len(detail_lines) - available_detail_rows + 1
        detail_lines = detail_lines[:max(0, available_detail_rows - 1)]
        detail_lines.append(f"... {hidden_line_count} more lines")

    for index, line in enumerate(detail_lines):
        attributes = curses.A_BOLD if index == 0 else 0
        safe_add_text(
            screen,
            selected_row + index + 1,
            column,
            line,
            attributes,
            panel_width
        )


def draw_dashboard(
    screen: curses.window,
    events: list[Event],
    selected_index: int | None,
    snapshot: dict[str, object] | None,
    paused: bool,
    completed: bool,
    validate: bool,
    error: BaseException | None
) -> None:
    screen.erase()
    height, width = screen.getmaxyx()

    if height < 24 or width < 100:
        safe_add_text(
            screen,
            0,
            0,
            "Terminal must be at least 100 columns by 24 rows."
        )
        screen.refresh()
        return

    divider_column = int(width * 0.56)
    divider_column = max(58, divider_column)
    divider_column = min(divider_column, width - 40)

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

    selected_event = get_selected_event(
        events,
        selected_index
    )

    draw_event_panel(
        screen,
        events,
        selected_index,
        divider_column
    )
    draw_book_panel(
        screen,
        snapshot,
        selected_event,
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
        f"[P] pause/resume  "
        f"[UP/DOWN] select event  "
        f"[C] clear  "
        f"[Q] quit  "
        f"Status: {status}  "
        f"Validation: {validation_status}"
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
    event_queue: Queue[Event],
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

    events: list[Event] = []
    selected_index: int | None = None
    snapshot: dict[str, object] | None = None
    worker_error: BaseException | None = None

    while True:
        new_events: list[Event] = []

        while True:
            try:
                new_events.append(event_queue.get_nowait())
            except Empty:
                break

        if new_events:
            events.extend(new_events)

            if len(events) > 2_000:
                removed_count = len(events) - 2_000
                events = events[removed_count:]

                if selected_index is not None:
                    selected_index = max(
                        0,
                        selected_index - removed_count
                    )

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
            selected_index = None

        if key in {curses.KEY_UP, ord("k"), ord("K")} and events:
            if selected_index is None:
                selected_index = max(0, len(events) - 2)
            else:
                selected_index = max(0, selected_index - 1)

        if key in {curses.KEY_DOWN, ord("j"), ord("J")}:
            if selected_index is not None:
                if selected_index >= len(events) - 2:
                    selected_index = None
                else:
                    selected_index += 1

        if key == curses.KEY_HOME and events:
            selected_index = 0

        if key == curses.KEY_END:
            selected_index = None

        draw_dashboard(
            screen=screen,
            events=events,
            selected_index=selected_index,
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

    event_queue: Queue[Event] = Queue()
    snapshot_queue: Queue[dict[str, object]] = Queue(maxsize=1)
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
