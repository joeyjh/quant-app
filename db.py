import sqlite3
import pandas as pd

from config import DB_PATH


def get_connection():
    return sqlite3.connect(DB_PATH)


def init_db():
    conn = get_connection()
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

    cur.execute("""
    CREATE TABLE IF NOT EXISTS mock_portfolios (
        snapshot_id TEXT,
        snapshot_date TEXT,
        preset_name TEXT,
        momentum_weight REAL,
        risk_weight REAL,
        value_weight REAL,
        quality_weight REAL,
        ticker TEXT,
        weight REAL,
        PRIMARY KEY (snapshot_id, ticker)
    )
    """)

    conn.commit()
    conn.close()


def save_price_to_db(ticker, df):
    if df is None or df.empty:
        return

    conn = get_connection()
    cur = conn.cursor()

    temp = df.copy().reset_index()

    date_col = None
    for col in temp.columns:
        if str(col).lower() in ["date", "datetime"]:
            date_col = col
            break

    if date_col is None:
        conn.close()
        return

    records = []

    for _, row in temp.iterrows():
        try:
            records.append((
                ticker,
                str(pd.to_datetime(row[date_col]).date()),
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


def load_price_from_db(ticker):
    conn = get_connection()

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


def save_fundamental_to_db(ticker, pe, margin, name, updated_at):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
    INSERT OR REPLACE INTO fundamentals
    (ticker, pe, margin, name, updated_at)
    VALUES (?, ?, ?, ?, ?)
    """, (ticker, pe, margin, name, updated_at))

    conn.commit()
    conn.close()


def load_fundamentals_from_db(tickers):
    if not tickers:
        return {}

    conn = get_connection()

    placeholders = ",".join(["?"] * len(tickers))
    query = f"""
    SELECT ticker, pe, margin, name, updated_at
    FROM fundamentals
    WHERE ticker IN ({placeholders})
    """

    df = pd.read_sql(query, conn, params=tickers)
    conn.close()

    result = {}
    for _, row in df.iterrows():
        result[row["ticker"]] = {
            "pe": row["pe"],
            "margin": row["margin"],
            "name": row["name"] if pd.notna(row["name"]) else row["ticker"],
            "updated_at": row["updated_at"]
        }

    return result


def save_mock_portfolio(snapshot_id, snapshot_date, preset_name, weights, tickers, weight_per_stock):
    conn = get_connection()
    cur = conn.cursor()

    momentum_w, risk_w, value_w, quality_w = weights

    records = []
    for ticker in tickers:
        records.append((
            snapshot_id,
            snapshot_date,
            preset_name,
            momentum_w,
            risk_w,
            value_w,
            quality_w,
            ticker,
            weight_per_stock
        ))

    cur.executemany("""
    INSERT OR REPLACE INTO mock_portfolios
    (
        snapshot_id,
        snapshot_date,
        preset_name,
        momentum_weight,
        risk_weight,
        value_weight,
        quality_weight,
        ticker,
        weight
    )
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, records)

    conn.commit()
    conn.close()


def list_mock_portfolio_snapshots():
    conn = get_connection()

    query = """
    SELECT
        snapshot_id,
        snapshot_date,
        preset_name,
        momentum_weight,
        risk_weight,
        value_weight,
        quality_weight,
        COUNT(*) as stock_count
    FROM mock_portfolios
    GROUP BY
        snapshot_id,
        snapshot_date,
        preset_name,
        momentum_weight,
        risk_weight,
        value_weight,
        quality_weight
    ORDER BY snapshot_date DESC, snapshot_id DESC
    """

    df = pd.read_sql(query, conn)
    conn.close()
    return df


def load_mock_portfolio(snapshot_id):
    conn = get_connection()

    query = """
    SELECT
        snapshot_id,
        snapshot_date,
        preset_name,
        momentum_weight,
        risk_weight,
        value_weight,
        quality_weight,
        ticker,
        weight
    FROM mock_portfolios
    WHERE snapshot_id = ?
    ORDER BY ticker
    """

    df = pd.read_sql(query, conn, params=(snapshot_id,))
    conn.close()
    return df


def delete_mock_portfolio(snapshot_id):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
    DELETE FROM mock_portfolios
    WHERE snapshot_id = ?
    """, (snapshot_id,))

    conn.commit()
    conn.close()