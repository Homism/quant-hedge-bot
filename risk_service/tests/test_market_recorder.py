from market_recorder.recorder import (
    cross_spread,
    quote_from_binance_book_ticker,
    quote_from_okx_books5,
)


def test_binance_book_ticker_quote_calculates_microstructure_fields() -> None:
    quote = quote_from_binance_book_ticker(
        {
            "e": "bookTicker",
            "u": 100,
            "s": "XAUTUSDT",
            "E": 1_000,
            "b": "2000.00",
            "B": "3.5",
            "a": "2001.00",
            "A": "2.5",
        },
        recv_ts_ms=1_125,
    )

    assert quote is not None
    assert quote.source == "binance_futures"
    assert quote.bid == 2000.0
    assert quote.ask == 2001.0
    assert quote.bid_size == 3.5
    assert quote.ask_size == 2.5
    assert quote.mid == 2000.5
    assert quote.spread == 1.0
    assert quote.latency_ms == 125


def test_okx_books5_quote_calculates_microstructure_fields() -> None:
    quote = quote_from_okx_books5(
        {
            "arg": {"channel": "books5", "instId": "XAUT-USDT"},
            "data": [
                {
                    "ts": "2_000".replace("_", ""),
                    "seqId": 88,
                    "bids": [["1999.50", "1.25", "0", "1"]],
                    "asks": [["2000.50", "1.75", "0", "2"]],
                }
            ],
        },
        recv_ts_ms=2_090,
    )

    assert quote is not None
    assert quote.source == "okx_public"
    assert quote.symbol == "XAUT-USDT"
    assert quote.bid == 1999.5
    assert quote.ask == 2000.5
    assert quote.bid_size == 1.25
    assert quote.ask_size == 1.75
    assert quote.mid == 2000.0
    assert quote.spread == 1.0
    assert quote.latency_ms == 90


def test_xaut_cross_spread_records_directional_edges() -> None:
    binance = quote_from_binance_book_ticker(
        {
            "e": "bookTicker",
            "u": 100,
            "s": "XAUTUSDT",
            "E": 1_000,
            "b": "2002.00",
            "B": "4",
            "a": "2003.00",
            "A": "5",
        },
        recv_ts_ms=1_050,
    )
    okx = quote_from_okx_books5(
        {
            "arg": {"channel": "books5", "instId": "XAUT-USDT"},
            "data": [
                {
                    "ts": "1000",
                    "bids": [["1999.00", "2", "0", "1"]],
                    "asks": [["2000.00", "3", "0", "1"]],
                }
            ],
        },
        recv_ts_ms=1_080,
    )

    spread = cross_spread(binance, okx)

    assert spread["available"] is True
    assert spread["mid_spread_abs"] == 3.0
    assert spread["sell_binance_buy_okx_abs"] == 2.0
    assert spread["sell_okx_buy_binance_abs"] == -4.0
    assert spread["best_direction"] == "sell_binance_buy_okx"
    assert spread["binance_latency_ms"] == 50
    assert spread["okx_latency_ms"] == 80

