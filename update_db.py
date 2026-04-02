from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

import pandas as pd
import yfinance as yf

from config import (
    PRICE_PERIOD,
    PRICE_CHUNK_SIZE,
    FUNDAMENTAL_WORKERS,
)
from db import (
    init_db,
    save_price_to_db,
    save_fundamental_to_db,
)
from universe import fetch_sp500_from_wikipedia, save_universe_csv


def chunk_list(items, chunk_size):
    for i in range(0, len(items), chunk_size):
        yield items[i:i + chunk_size]


def extract_price_frame(raw, ticker, is_single):
    try:
        if is_single:
            df = raw.copy()
        else:
            if ticker not in raw.columns.get_level_values(0):
                return None
            df = raw[ticker].copy()

        if df is None or df.empty:
            return None

        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        needed = ["Open", "High", "Low", "Close", "Volume"]
        for col in needed:
            if col not in df.columns:
                return None

        return df[needed].dropna(how="all")
    except Exception:
        return None


def update_prices(tickers):
    print(f"[1/2] price data update start: {len(tickers)} tickers")

    saved = 0

    for idx, chunk in enumerate(chunk_list(tickers, PRICE_CHUNK_SIZE), start=1):
        print(f"  - chunk {idx}: {len(chunk)} tickers")

        try:
            raw = yf.download(
                chunk,
                period=PRICE_PERIOD,
                group_by="ticker",
                auto_adjust=False,
                progress=False,
                threads=True,
            )
        except Exception as e:
            print(f"    price chunk download failed: {e}")
            continue

        is_single = len(chunk) == 1

        for ticker in chunk:
            df = extract_price_frame(raw, ticker, is_single)
            if df is None or df.empty:
                continue

            save_price_to_db(ticker, df)
            saved += 1

    print(f"price data update done: {saved} tickers saved")


def fetch_single_fundamental(ticker):
    try:
        info = yf.Ticker(ticker).info

        pe = info.get("trailingPE", None)
        margin = info.get("profitMargins", None)
        name = info.get("shortName", ticker)

        return ticker, pe, margin, name
    except Exception:
        return ticker, None, None, ticker


def update_fundamentals(tickers):
    print(f"[2/2] fundamentals update start: {len(tickers)} tickers")

    updated_at = datetime.now().isoformat()
    saved = 0

    with ThreadPoolExecutor(max_workers=FUNDAMENTAL_WORKERS) as executor:
        futures = [executor.submit(fetch_single_fundamental, ticker) for ticker in tickers]

        for future in as_completed(futures):
            ticker, pe, margin, name = future.result()
            save_fundamental_to_db(ticker, pe, margin, name, updated_at)
            saved += 1

            if saved % 50 == 0:
                print(f"  - fundamentals saved: {saved}")

    print(f"fundamentals update done: {saved} tickers saved")


def main():
    print("update_db.py start")
    init_db()

    universe_df = fetch_sp500_from_wikipedia()
    save_universe_csv(universe_df)

    tickers = universe_df["ticker"].tolist()
    print(f"S&P500 universe loaded: {len(tickers)} tickers")

    update_prices(tickers)
    update_fundamentals(tickers)

    print("update_db.py finished")


if __name__ == "__main__":
    main()