import pandas as pd


MOMENTUM_LOOKBACK = 252      # 약 12개월
MOMENTUM_SKIP = 21           # 최근 1개월 제외
VOL_LOOKBACK = 126           # 최근 6개월 변동성
MIN_HISTORY = 252            # 최소 필요 데이터

TOP_N = 10
BUFFER_N = 15


def safe_rank_score(series, ascending=True):
    if len(series) == 0:
        return pd.Series(dtype=float)

    ranked = series.rank(pct=True, ascending=ascending)

    if ranked.isna().all():
        return pd.Series([0.5] * len(series), index=series.index)

    return ranked.fillna(0.5)


def winsorize_series(series, lower=0.02, upper=0.98):
    if len(series) == 0:
        return series

    low = series.quantile(lower)
    high = series.quantile(upper)

    return series.clip(lower=low, upper=high)


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

            if len(df) < MIN_HISTORY:
                continue

            close = df["Close"].dropna()

            if len(close) < MIN_HISTORY:
                continue

            # 12-1 Momentum
            current_price = close.iloc[-1 - MOMENTUM_SKIP]
            past_price = close.iloc[-1 - MOMENTUM_SKIP - MOMENTUM_LOOKBACK + 1]

            if pd.isna(current_price) or pd.isna(past_price) or past_price <= 0:
                continue

            momentum = (current_price / past_price) - 1

            # 최근 6개월 변동성
            daily_returns = close.pct_change().dropna()
            recent_returns = daily_returns.iloc[-VOL_LOOKBACK:]

            if len(recent_returns) < 60:
                continue

            volatility = recent_returns.std() * (252 ** 0.5)

            fund = fundamentals.get(ticker, {})
            pe = fund.get("pe", None)
            margin = fund.get("margin", None)

            # Value
            if pe is None or pd.isna(pe) or pe <= 0:
                continue
            value = 1 / pe

            # Quality
            if margin is None or pd.isna(margin):
                continue
            quality = margin

            results.append({
                "Ticker": ticker,
                "momentum": momentum,
                "volatility": volatility,
                "value": value,
                "quality": quality
            })

        except Exception:
            continue

    df_result = pd.DataFrame(results)

    if df_result.empty:
        return df_result

    for col in ["momentum", "volatility", "value", "quality"]:
        df_result[col] = pd.to_numeric(df_result[col], errors="coerce")

    df_result = df_result.dropna().reset_index(drop=True)

    if df_result.empty:
        return df_result

    # 극단값 완화
    df_result["momentum"] = winsorize_series(df_result["momentum"])
    df_result["volatility"] = winsorize_series(df_result["volatility"])
    df_result["value"] = winsorize_series(df_result["value"])
    df_result["quality"] = winsorize_series(df_result["quality"])

    return df_result


def calculate_factors(data, fundamentals, tickers):
    return build_factor_frame(data, fundamentals, tickers)


def calculate_scores(df, weights):
    momentum_w, risk_w, value_w, quality_w = weights

    df = df.copy()

    # percentile rank 기반 점수
    df["momentum_score"] = safe_rank_score(df["momentum"], ascending=True)
    df["risk_score"] = safe_rank_score(df["volatility"], ascending=False)   # 낮을수록 좋음
    df["value_score"] = safe_rank_score(df["value"], ascending=True)
    df["quality_score"] = safe_rank_score(df["quality"], ascending=True)

    df["score"] = (
        df["momentum_score"] * momentum_w +
        df["risk_score"] * risk_w +
        df["value_score"] * value_w +
        df["quality_score"] * quality_w
    )

    return df.sort_values("score", ascending=False).reset_index(drop=True)


def select_portfolio_with_buffer(scored_df, prev_holdings, top_n=TOP_N, buffer_n=BUFFER_N):
    ranked_df = scored_df.reset_index(drop=True).copy()
    ranked_df["rank"] = range(1, len(ranked_df) + 1)

    rank_map = dict(zip(ranked_df["Ticker"], ranked_df["rank"]))

    kept = []
    for ticker in prev_holdings:
        rank = rank_map.get(ticker, None)
        if rank is not None and rank <= buffer_n:
            kept.append(ticker)

    selected = kept.copy()

    for ticker in ranked_df["Ticker"]:
        if ticker in selected:
            continue

        rank = rank_map.get(ticker, None)
        if rank is not None and rank <= top_n:
            selected.append(ticker)

        if len(selected) >= top_n:
            break

    if len(selected) < top_n:
        for ticker in ranked_df["Ticker"]:
            if ticker in selected:
                continue
            selected.append(ticker)
            if len(selected) >= top_n:
                break

    selected = selected[:top_n]
    portfolio_df = ranked_df[ranked_df["Ticker"].isin(selected)].copy()

    # 원래 순위 순서 유지
    portfolio_df["sort_rank"] = portfolio_df["Ticker"].map(rank_map)
    portfolio_df = portfolio_df.sort_values("sort_rank").drop(columns=["sort_rank"])

    return portfolio_df


def backtest_strategy(data, fundamentals, tickers, weights):
    portfolio_returns = []
    portfolio_dates = []

    dates = None
    for ticker in tickers:
        df = data.get(ticker, None)
        if df is not None and not df.empty:
            dates = df.index
            break

    if dates is None:
        return None, []

    monthly_dates = dates[::21]

    prev_holdings = []
    turnovers = []

    for i in range(len(monthly_dates) - 1):
        start = monthly_dates[i]
        end = monthly_dates[i + 1]

        df_temp = build_factor_frame(data, fundamentals, tickers, end_date=start)

        if df_temp.empty or len(df_temp) < TOP_N:
            continue

        scored_df = calculate_scores(df_temp, weights)
        top = select_portfolio_with_buffer(scored_df, prev_holdings, top_n=TOP_N, buffer_n=BUFFER_N)

        current_holdings = top["Ticker"].tolist()

        if prev_holdings:
            changed = len(set(current_holdings) - set(prev_holdings))
            turnover = changed / len(current_holdings) if len(current_holdings) > 0 else 0
            turnovers.append(turnover)

        prev_holdings = current_holdings

        period_returns = []

        for ticker in current_holdings:
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
        portfolio_dates.append(end)

    if len(portfolio_returns) == 0:
        return None, turnovers

    bt_series = pd.Series(portfolio_returns, index=pd.to_datetime(portfolio_dates)).sort_index().cumsum()
    return bt_series, turnovers