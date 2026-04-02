import pandas as pd
import streamlit as st

from config import MIN_PRICE_ROWS
from db import init_db, load_price_from_db, load_fundamentals_from_db
from universe import get_universe_tickers


@st.cache_data
def get_sp500():
    return get_universe_tickers()


@st.cache_data(ttl=3600)
def load_all_data(tickers):
    init_db()

    result = {}

    for ticker in tickers:
        df = load_price_from_db(ticker)

        if df is None or df.empty:
            continue

        if len(df) < MIN_PRICE_ROWS:
            continue

        result[ticker] = df

    return result


@st.cache_data(ttl=86400)
def get_fundamentals(tickers):
    init_db()

    db_data = load_fundamentals_from_db(tickers)
    result = {}

    for ticker in tickers:
        item = db_data.get(ticker, None)

        if item is None:
            result[ticker] = {
                "pe": None,
                "margin": None,
                "name": ticker
            }
        else:
            result[ticker] = {
                "pe": item.get("pe", None),
                "margin": item.get("margin", None),
                "name": item.get("name", ticker) or ticker
            }

    return result


@st.cache_data
def get_chart(ticker):
    init_db()

    df = load_price_from_db(ticker)
    if df is None:
        return pd.DataFrame()

    return df