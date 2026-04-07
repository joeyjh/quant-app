import pandas as pd


def parse_holdings(text):
    if not text:
        return []

    items = [x.strip().upper() for x in text.replace("\n", ",").split(",")]
    items = [x for x in items if x]

    seen = set()
    result = []
    for item in items:
        if item not in seen:
            seen.add(item)
            result.append(item)

    return result


def enrich_table(df_portfolio, fundamentals):
    table = df_portfolio.copy()

    table["Company"] = table["Ticker"].apply(
        lambda x: fundamentals.get(x, {}).get("name", x)
    )
    table["Company"] = table["Company"] + " (" + table["Ticker"] + ")"

    table["momentum"] = table["momentum"].round(4)
    table["volatility"] = table["volatility"].round(4)
    table["value"] = table["value"].round(4)
    table["quality"] = table["quality"].round(4)
    table["score"] = table["score"].round(3)

    table = table.rename(columns={
        "momentum": "Momentum (12-1M)",
        "volatility": "Risk (Vol)",
        "value": "Value Score",
        "quality": "Quality Score",
        "score": "Total Score"
    })

    return table


def format_ticker_list(tickers, fundamentals):
    if not tickers:
        return ["해당 없음"]

    result = []
    for ticker in tickers:
        name = fundamentals.get(ticker, {}).get("name", ticker)
        result.append(f"{name} ({ticker})")
    return result


def metric_text(value, kind="percent", digits=2):
    if value is None:
        return "-"

    if kind == "percent":
        return f"{value:.{digits}%}"
    if kind == "float":
        return f"{value:.{digits}f}"
    if kind == "int":
        return f"{int(value)}"

    return str(value)


def apply_period_filter(df, period_label, period_options):
    if df is None or len(df) == 0:
        return df

    periods = period_options[period_label]
    if periods is None:
        return df.copy()

    filtered = df.copy()

    if isinstance(filtered.index, pd.DatetimeIndex):
        end_date = filtered.index.max()
        start_date = end_date - pd.Timedelta(days=periods)
        return filtered.loc[filtered.index >= start_date].copy()

    return filtered.tail(periods).copy()