# Python Limit Order Book

A Python implementation of an exchange-style limit order book with a stochastic order-flow simulator and terminal dashboard.

## Requirements

- Python 3.10 or later
- A terminal that supports `curses`

The dashboard uses only the Python standard library. On Windows, run it through WSL or another terminal environment that supports `curses`.

## Setup

Clone the repository and move into its root directory:

```bash
git clone https://github.com/sachin-peterson/limit_order_book.git
cd limit_order_book
```

Create and activate a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Install the project:

```bash
python3 -m pip install --upgrade pip
python3 -m pip install -e .
```

## Run the dashboard

Run the command from the repository root:

```bash
python3 -m order_book_python.cli.run_dashboard \
    --actions 1000 \
    --seed 42 \
    --validate \
    --request-delay 1 \
    --depth 5
```

Dashboard controls:

- `P`: pause or resume the simulation
- `C`: clear the event stream
- `Q`: quit

The terminal must be at least 90 columns wide and 20 rows high.

You can also use the Makefile:

```bash
make dashboard
```

Command-line options are available with:

```bash
python3 -m order_book_python.cli.run_dashboard --help
```

## Run without the dashboard

To print generated events and the final order-book snapshot directly to the terminal:

```bash
python3 -m order_book_python.cli.run_simulation \
    --actions 1000 \
    --seed 42 \
    --validate
```

Or use:

```bash
make simulation
```

## Run the tests

Install the development dependencies and run the test suite:

```bash
python3 -m pip install -e ".[dev]"
python3 -m pytest order_book_python/tests
```

Or use:

```bash
make install-dev
make test
```