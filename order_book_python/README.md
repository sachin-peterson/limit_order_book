# Python Limit Order Book

A Python implementation of a limit order book, matching engine, stochastic order-flow simulator, and terminal dashboard

## Requirements

- Python 3.10 or later
- A terminal with `curses` support

The project uses only the Python standard library at runtime.

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
make install
```

You can also install it directly:

```bash
python3 -m pip install -e .
```

## Run the dashboard

From the repository root:

```bash
python3 -m order_book_python.cli.run_dashboard \
    --actions 1000 \
    --seed 42 \
    --validate \
    --request-delay 1 \
    --depth 5
```

Or use:

```bash
make dashboard
```

The Makefile arguments can be overridden:

```bash
make dashboard ACTIONS=500 SEED=10 REQUEST_DELAY=0.5 DEPTH=10
```

## Run the tests

The tests use Python's built-in `unittest` module. No testing dependency is required.

```bash
make test
```

Equivalent command:

```bash
python3 -m unittest discover \
    -s order_book_python/tests \
    -t . \
    -p "test_*.py" \
    -v
```