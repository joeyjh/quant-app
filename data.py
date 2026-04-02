import sqlite3
from datetime import datetime, timedelta

import pandas as pd
import requests
import streamlit as st
import yfinance as yf


DB_PATH = "quant.db"
PRICE_MAX_AGE_DAYS = 7
FUNDAMENTAL_MAX_AGE_DAYS = 30


# =========================
# DB 초기화
# =========================
def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS prices (
        ticker TEXT,
        date TEXT,
        open REAL,
        high REAL,
        low REAL,
        close REAL,
        volume REAL,
        PRIMARY KEY (ticker, date)
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS fundamentals (
        ticker TEXT PRIMARY KEY,
        pe REAL,
        margin REAL,
        name TEXT,
        updated_at TEXT
    )
    """)

    conn.commit()
    conn.close()


# =========================
# S&P500 티커 가져오기
# =========================
@st.cache_data
def get_sp500():
    try:
        url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()

        tables = pd.read_html(response.text)
        tickers = tables[0]["Symbol"].tolist()

        return tickers[:100]

    except Exception:
        return [
            "AAPL", "MSFT", "GOOGL", "AMZN", "META",
            "NVDA", "TSLA", "BRK-B", "JPM", "XOM",
            "LLY", "AVGO", "UNH", "V", "COST",
            "PG", "JNJ", "HD", "MA", "MRK"
        ]


# =========================
# 가격 데이터 DB 저장
# =========================
def save_price_to_db(ticker, df):
    if df is None or df.empty:
        return

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    df = df.reset_index().copy()

    if "Date" not in df.columns:
        conn.close()
        return

    records = []
    for _, row in df.iterrows():
        try:
            records.append((
                ticker,
                str(pd.to_datetime(row["Date"]).date()),
                float(row["Open"]) if pd.notna(row["Open"]) else None,
                float(row["High"]) if pd.notna(row["High"]) else None,
                float(row["Low"]) if pd.notna(row["Low"]) else None,
                float(row["Close"]) if pd.notna(row["Close"]) else None,
                float(row["Volume"]) if pd.notna(row["Volume"]) else None,
            ))
        except Exception:
            continue

    cur.executemany("""
    INSERT OR REPLACE INTO prices
    (ticker, date, open, high, low, close, volume)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    """, records)

    conn.commit()
    conn.close()


# =========================
# DB에서 가격 데이터 불러오기
# =========================
def load_price_from_db(ticker):
    conn = sqlite3.connect(DB_PATH)

    query = """
    SELECT date, open, high, low, close, volume
    FROM prices
    WHERE ticker = ?
    ORDER BY date
    """

    df = pd.read_sql(query, conn, params=(ticker,))
    conn.close()

    if df.empty:
        return None

    df["date"] = pd.to_datetime(df["date"])
    df = df.set_index("date")

    df = df.rename(columns={
        "open": "Open",
        "high": "High",
        "low": "Low",
        "close": "Close",
        "volume": "Volume"
    })

    return df


# =========================
# 가격 데이터 최신 여부 확인
# =========================
def is_price_data_stale(df, max_age_days=PRICE_MAX_AGE_DAYS):
    if df is None or df.empty:
        return True

    try:
        last_date = pd.to_datetime(df.index.max()).date()
        today = datetime.now().date()
        return (today - last_date).days > max_age_days
    except Exception:
        return True


# =========================
# 가격 데이터 다운로드
# =========================
def download_price_data(ticker):
    try:
        df = yf.download(ticker, period="2y", progress=False, auto_adjust=False)

        if df is None or df.empty:
            return None

        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        needed = ["Open", "High", "Low", "Close", "Volume"]
        for col in needed:
            if col not in df.columns:
                return None

        return df[needed].copy()

    except Exception:
        return None


# =========================
# 전체 가격 데이터 로드
# =========================
@st.cache_data(ttl=3600)
def load_all_data(tickers):
    init_db()
    result = {}

    for ticker in tickers:
        df = load_price_from_db(ticker)

        # DB 데이터가 있고 너무 오래되지 않았으면 사용
        if df is not None and len(df) >= 200 and not is_price_data_stale(df):
            result[ticker] = df
            continue

        # 오래됐거나 없으면 재다운로드
        fresh_df = download_price_data(ticker)

        if fresh_df is not None and not fresh_df.empty:
            save_price_to_db(ticker, fresh_df)
            result[ticker] = fresh_df
        elif df is not None and len(df) >= 200:
            # 다운로드 실패 시 기존 DB fallback
            result[ticker] = df

    return result


# =========================
# fundamentals 저장
# =========================
def save_fundamental_to_db(ticker, pe, margin, name):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("""
    INSERT OR REPLACE INTO fundamentals
    (ticker, pe, margin, name, updated_at)
    VALUES (?, ?, ?, ?, ?)
    """, (
        ticker,
        float(pe) if pe is not None and pd.notna(pe) else None,
        float(margin) if margin is not None and pd.notna(margin) else None,
        name,
        datetime.now().isoformat()
    ))

    conn.commit()
    conn.close()


# =========================
# fundamentals DB 조회
# =========================
def load_fundamental_from_db(ticker):
    conn = sqlite3.connect(DB_PATH)

    query = """
    SELECT ticker, pe, margin, name, updated_at
    FROM fundamentals
    WHERE ticker = ?
    """

    df = pd.read_sql(query, conn, params=(ticker,))
    conn.close()

    if df.empty:
        return None

    return df.iloc[0].to_dict()


# =========================
# fundamentals 최신 여부 확인
# =========================
def is_fundamental_data_stale(db_data, max_age_days=FUNDAMENTAL_MAX_AGE_DAYS):
    if db_data is None:
        return True

    updated_at = db_data.get("updated_at", None)
    if not updated_at:
        return True

    try:
        updated_dt = pd.to_datetime(updated_at)
        now = datetime.now()
        return (now - updated_dt).days > max_age_days
    except Exception:
        return True


# =========================
# 개별 fundamentals 다운로드
# =========================
def fetch_single_fundamental(ticker):
    try:
        info = yf.Ticker(ticker).info

        pe = info.get("trailingPE", None)
        margin = info.get("profitMargins", None)
        name = info.get("shortName", ticker)

        return {
            "pe": pe,
            "margin": margin,
            "name": name
        }

    except Exception:
        return {
            "pe": None,
            "margin": None,
            "name": ticker
        }


# =========================
# fundamentals 전체 로드
# =========================
@st.cache_data(ttl=86400)
def get_fundamentals(tickers):
    init_db()
    result = {}

    for ticker in tickers:
        db_data = load_fundamental_from_db(ticker)

        # DB 데이터가 있고 너무 오래되지 않았으면 사용
        if db_data is not None and not is_fundamental_data_stale(db_data):
            result[ticker] = {
                "pe": db_data.get("pe", None),
                "margin": db_data.get("margin", None),
                "name": db_data.get("name", ticker) or ticker
            }
            continue

        # 오래됐거나 없으면 재다운로드
        fetched = fetch_single_fundamental(ticker)

        # 다운로드 성공 여부와 상관없이 저장
        save_fundamental_to_db(
            ticker,
            fetched["pe"],
            fetched["margin"],
            fetched["name"]
        )

        # 다운로드 실패 시 기존 DB가 있으면 fallback
        if fetched["pe"] is None and fetched["margin"] is None and db_data is not None:
            result[ticker] = {
                "pe": db_data.get("pe", None),
                "margin": db_data.get("margin", None),
                "name": db_data.get("name", ticker) or ticker
            }
        else:
            result[ticker] = fetched

    return result


# =========================
# 차트 데이터
# =========================
@st.cache_data
def get_chart(ticker):
    init_db()

    df = load_price_from_db(ticker)
    if df is not None and not df.empty:
        return df

    df = download_price_data(ticker)
    if df is not None and not df.empty:
        save_price_to_db(ticker, df)
        return df

    return pd.DataFrame()