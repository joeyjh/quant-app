import pandas as pd
import yfinance as yf
import requests
import streamlit as st


@st.cache_data
def get_sp500():
    url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
    
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(url, headers=headers)
    tables = pd.read_html(response.text)
    
    return tables[0]["Symbol"].tolist()


@st.cache_data(ttl=3600)
def load_all_data(tickers):
    return yf.download(
        tickers,
        period="2y",
        group_by='ticker',
        threads=True,
        progress=False
    )


from concurrent.futures import ThreadPoolExecutor


def fetch_single_fundamental(t):
    try:
        info = yf.Ticker(t).info

        pe = info.get("trailingPE", None)
        margin = info.get("profitMargins", None)
        name = info.get("shortName", t)

        return t, {
            "pe": pe,
            "margin": margin,
            "name": name
        }
    except Exception:
        return t, {
            "pe": None,
            "margin": None,
            "name": t
        }


@st.cache_data(ttl=86400)
def get_fundamentals(tickers):
    result = {}

    with ThreadPoolExecutor(max_workers=20) as executor:
        futures = executor.map(fetch_single_fundamental, tickers)

        for ticker, data in futures:
            result[ticker] = data

    return result

@st.cache_data
def get_chart(ticker):
    return yf.download(ticker, period="2y", progress=False)