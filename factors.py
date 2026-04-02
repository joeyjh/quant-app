import pandas as pd


def safe_zscore(series):
    std = series.std()
    if std == 0 or pd.isna(std):
        return pd.Series([0] * len(series), index=series.index)
    return (series - series.mean()) / std


def build_factor_frame(data, fundamentals, tickers, end_date=None):
    results = []

    for ticker in tickers:
        try:
            df = data.get(ticker, None)
            if df is None or df.empty:
                continue

            if end_date is not None:
                df = df.loc[:end_date]

            if df is None or df.empty:
                continue

            if len(df) < 121:
                continue

            ret = df["Close"].pct_change(120).iloc[-1]
            if pd.isna(ret):
                continue

            vol = df["Close"].pct_change().std()

            fund = fundamentals.get(ticker, {})
            pe = fund.get("pe", None)
            margin = fund.get("margin", None)

            if pe is None or pd.isna(pe) or pe <= 0:
                continue

            if margin is None or pd.isna(margin):
                continue

            value = 1 / pe
            quality = margin

            results.append({
                "Ticker": ticker,
                "return": ret,
                "volatility": vol,
                "value": value,
                "quality": quality
            })

        except Exception:
            continue

    df_result = pd.DataFrame(results)

    if df_result.empty:
        return df_result

    df_result["return"] = pd.to_numeric(df_result["return"], errors="coerce")
    df_result["volatility"] = pd.to_numeric(df_result["volatility"], errors="coerce")
    df_result["value"] = pd.to_numeric(df_result["value"], errors="coerce")
    df_result["quality"] = pd.to_numeric(df_result["quality"], errors="coerce")

    df_result = df_result.dropna().reset_index(drop=True)
    return df_result


def calculate_factors(data, fundamentals, tickers):
    return build_factor_frame(data, fundamentals, tickers)


def calculate_scores(df, weights):
    momentum_w, risk_w, value_w, quality_w = weights

    df = df.copy()

    df["momentum_z"] = safe_zscore(df["return"])
    df["risk_z"] = safe_zscore(df["volatility"])
    df["value_z"] = safe_zscore(df["value"])
    df["quality_z"] = safe_zscore(df["quality"])

    df["risk_z"] = -df["risk_z"]

    df["score"] = (
        df["momentum_z"] * momentum_w +
        df["risk_z"] * risk_w +
        df["value_z"] * value_w +
        df["quality_z"] * quality_w
    )

    return df.sort_values("score", ascending=False).reset_index(drop=True)


def backtest_strategy(data, fundamentals, tickers, weights):
    portfolio_returns = []

    dates = None
    for ticker in tickers:
        df = data.get(ticker, None)
        if df is not None and not df.empty:
            dates = df.index
            break

    if dates is None:
        return None, []

    monthly_dates = dates[::21]

    prev_top = set()
    turnovers = []

    for i in range(len(monthly_dates) - 1):
        start = monthly_dates[i]
        end = monthly_dates[i + 1]

        df_temp = build_factor_frame(data, fundamentals, tickers, end_date=start)

        if df_temp.empty or len(df_temp) < 5:
            continue

        df_temp = calculate_scores(df_temp, weights)
        top = df_temp.head(10)

        current_top = set(top["Ticker"])

        if prev_top:
            changed = len(current_top - prev_top)
            turnover = changed / len(current_top) if len(current_top) > 0 else 0
            turnovers.append(turnover)

        prev_top = current_top

        period_returns = []

        for ticker in top["Ticker"]:
            df = data.get(ticker, None)
            if df is None or df.empty:
                continue

            try:
                start_price = df.loc[start]["Close"]
                end_price = df.loc[end]["Close"]

                cost = 0.002
                slippage = 0.001

                r = ((end_price * (1 - slippage)) / (start_price * (1 + slippage))) - 1 - cost
                period_returns.append(r)
            except Exception:
                continue

        if len(period_returns) == 0:
            continue

        portfolio_returns.append(sum(period_returns) / len(period_returns))

    if len(portfolio_returns) == 0:
        return None, turnovers

    return pd.Series(portfolio_returns).cumsum(), turnovers