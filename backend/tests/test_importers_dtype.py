"""Regression test for symbol leading-zero / numpy dtype bug.

``read_table`` previously used pandas default dtype inference, which (a)
parsed numeric-looking columns into numpy scalar types (not adaptable by
psycopg2) and (b) stripped leading zeros from symbol-like columns such as
"0050" -> 50. Both are fixed by reading everything as plain strings.
"""

from __future__ import annotations

from pathlib import Path

from app.utils.importers import _clean, _num, read_table


def test_read_table_preserves_leading_zero_symbol(tmp_path: Path) -> None:
    csv_path = tmp_path / "sample.csv"
    csv_path.write_text("symbol,price,empty_col\n0050,123.45,\n006208,67.0,\n")

    df = read_table(csv_path)

    symbols = df["symbol"].tolist()
    assert symbols == ["0050", "006208"]
    for symbol in symbols:
        assert isinstance(symbol, str)


def test_read_table_values_are_plain_strings(tmp_path: Path) -> None:
    csv_path = tmp_path / "sample.csv"
    csv_path.write_text("symbol,price,empty_col\n0050,123.45,\n")

    df = read_table(csv_path)
    row = df.iloc[0]

    # All raw cell values from read_table must be plain Python strings.
    for col in ("symbol", "price", "empty_col"):
        value = row[col]
        assert isinstance(value, str)
        assert type(value).__module__ == "builtins"


def test_clean_and_num_produce_native_python_types(tmp_path: Path) -> None:
    csv_path = tmp_path / "sample.csv"
    csv_path.write_text("symbol,price,empty_col\n0050,123.45,\n")

    df = read_table(csv_path)
    row = df.iloc[0]

    symbol = _clean(row["symbol"])
    price = _num(row["price"])
    empty = _clean(row["empty_col"])

    assert symbol == "0050"
    assert isinstance(symbol, str)

    assert price == 123.45
    assert isinstance(price, float)
    assert type(price).__module__ == "builtins"

    assert empty is None
