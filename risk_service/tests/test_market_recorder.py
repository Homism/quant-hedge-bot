from market_recorder.recorder import (
    append_hourly_snapshot,
    hourly_snapshot_path,
    maintain_hourly_retention,
    cross_spread,
    quote_from_binance_book_ticker,
    quote_from_okx_books5,
    retention_summary,
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


def test_hourly_retention_writes_compresses_and_deletes_old_files(tmp_path) -> None:
    symbol = "XAUTUSDT"
    current_ms = 1_784_044_800_000  # 2026-07-14T16:00:00Z
    old_ms = current_ms - 3 * 60 * 60 * 1000
    previous_ms = current_ms - 60 * 60 * 1000
    payload = {
        "updated_at_ms": current_ms,
        "read_only": True,
        "trading_enabled": False,
        "quotes": {},
    }

    current_path = append_hourly_snapshot(tmp_path, symbol, payload)
    assert current_path == hourly_snapshot_path(tmp_path, symbol, current_ms)
    assert current_path.exists()

    old_path = hourly_snapshot_path(tmp_path, symbol, old_ms)
    old_path.write_text('{"old":true}\n', encoding="utf-8")
    previous_path = hourly_snapshot_path(tmp_path, symbol, previous_ms)
    previous_path.write_text('{"previous":true}\n', encoding="utf-8")

    summary = maintain_hourly_retention(tmp_path, symbol, retention_hours=2, current_timestamp_ms=current_ms)

    assert not old_path.exists()
    assert not (old_path.with_suffix(f"{old_path.suffix}.gz")).exists()
    assert not previous_path.exists()
    assert previous_path.with_suffix(f"{previous_path.suffix}.gz").exists()
    assert current_path.exists()
    assert summary["retention_hours_target"] == 2
    assert summary["retained_hours"] == 2
    assert summary["compressed_file_count"] == 1
    assert summary["uncompressed_file_count"] == 1


def test_retention_summary_reports_hourly_disk_usage(tmp_path) -> None:
    symbol = "XAUTUSDT"
    timestamp_ms = 1_784_044_800_000
    append_hourly_snapshot(tmp_path, symbol, {"updated_at_ms": timestamp_ms, "x": 1})
    summary = retention_summary(tmp_path, symbol)

    assert summary["file_count"] == 1
    assert summary["retained_hours"] == 1
    assert summary["total_bytes"] > 0
    assert summary["oldest_hour"] == "2026-07-14T16:00:00Z"
    assert summary["newest_hour"] == "2026-07-14T16:00:00Z"
