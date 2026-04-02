import pandas as pd
import requests

from config import UNIVERSE_CSV_PATH


def normalize_ticker(symbol):
    return str(symbol).replace(".", "-").strip().upper()


def fetch_sp500_from_wikipedia():
    url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
    headers = {"User-Agent": "Mozilla/5.0"}

    response = requests.get(url, headers=headers, timeout=10)
    response.raise_for_status()

    tables = pd.read_html(response.text)
    df = tables[0][["Symbol", "Security"]].copy()

    df.columns = ["ticker", "company"]
    df["ticker"] = df["ticker"].apply(normalize_ticker)

    df = df.drop_duplicates(subset=["ticker"]).reset_index(drop=True)
    return df


def save_universe_csv(df):
    df.to_csv(UNIVERSE_CSV_PATH, index=False, encoding="utf-8-sig")


def load_universe_csv():
    df = pd.read_csv(UNIVERSE_CSV_PATH)
    df["ticker"] = df["ticker"].apply(normalize_ticker)
    return df.drop_duplicates(subset=["ticker"]).reset_index(drop=True)


def get_universe_df():
    try:
        return load_universe_csv()
    except Exception:
        df = fetch_sp500_from_wikipedia()
        save_universe_csv(df)
        return df


def get_universe_tickers():
    df = get_universe_df()
    return df["ticker"].tolist()
