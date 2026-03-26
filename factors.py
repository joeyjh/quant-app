import pandas as pd


def calculate_factors(data, fundamentals, tickers):
    results = []

    for ticker in tickers:
        try:
            df = data[ticker]

            if df is None or df.empty:
                continue

            # Momentum
            ret = df['Close'].pct_change(120).iloc[-1]
            if pd.isna(ret):
                continue

            # Risk
            vol = df['Close'].pct_change().std()

            fund = fundamentals.get(ticker, {})
            pe = fund.get("pe", None)
            margin = fund.get("margin", None)

            # Value
            if pe is None or pe <= 0:
                continue
            value = 1 / pe

            # Quality
            if margin is None:
                continue
            quality = margin

            results.append({
                "Ticker": ticker,
                "return": ret,
                "volatility": vol,
                "value": value,
                "quality": quality
            })

        except:
            continue

    df = pd.DataFrame(results)

    df["return"] = pd.to_numeric(df["return"], errors="coerce")
    df["volatility"] = pd.to_numeric(df["volatility"], errors="coerce")

    df = df.dropna().reset_index(drop=True)

    return df


def calculate_scores(df, weights):
    momentum_w, risk_w, value_w, quality_w = weights

    # z-score
    df["momentum_z"] = (df["return"] - df["return"].mean()) / df["return"].std()
    df["risk_z"] = (df["volatility"] - df["volatility"].mean()) / df["volatility"].std()
    df["value_z"] = (df["value"] - df["value"].mean()) / df["value"].std()
    df["quality_z"] = (df["quality"] - df["quality"].mean()) / df["quality"].std()

    df["risk_z"] = -df["risk_z"]

    df["score"] = (
        df["momentum_z"] * momentum_w +
        df["risk_z"] * risk_w +
        df["value_z"] * value_w +
        df["quality_z"] * quality_w
    )

    return df.sort_values("score", ascending=False)

def backtest_strategy(data, fundamentals, tickers, weights):
    portfolio_returns = []

    dates = None

    for ticker in tickers:
        df = data[ticker]
        if df is not None and not df.empty:
            dates = df.index
            break

    if dates is None:
        return None

    # 매월 리밸런싱
    monthly_dates = dates[::21]  # 대략 1개월

    for i in range(len(monthly_dates) - 1):
        start = monthly_dates[i]
        end = monthly_dates[i + 1]

        results = []

        for ticker in tickers:
            try:
                df = data[ticker]
                df_period = df.loc[:start]

                if len(df_period) < 120:
                    continue

                # Momentum
                ret = df_period['Close'].pct_change(120).iloc[-1]
                if pd.isna(ret):
                    continue

                # Risk
                vol = df_period['Close'].pct_change().std()

                fund = fundamentals.get(ticker, {})
                pe = fund.get("pe", None)
                margin = fund.get("margin", None)

                if pe is None or pe <= 0 or margin is None:
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

            except:
                continue

        df_temp = pd.DataFrame(results)

        if len(df_temp) < 10:
            continue

        # z-score
        df_temp["momentum_z"] = (df_temp["return"] - df_temp["return"].mean()) / df_temp["return"].std()
        df_temp["risk_z"] = (df_temp["volatility"] - df_temp["volatility"].mean()) / df_temp["volatility"].std()
        df_temp["value_z"] = (df_temp["value"] - df_temp["value"].mean()) / df_temp["value"].std()
        df_temp["quality_z"] = (df_temp["quality"] - df_temp["quality"].mean()) / df_temp["quality"].std()

        df_temp["risk_z"] = -df_temp["risk_z"]

        momentum_w, risk_w, value_w, quality_w = weights

        df_temp["score"] = (
            df_temp["momentum_z"] * momentum_w +
            df_temp["risk_z"] * risk_w +
            df_temp["value_z"] * value_w +
            df_temp["quality_z"] * quality_w
        )

        top = df_temp.sort_values("score", ascending=False).head(10)

        # 다음 기간 수익률
        period_returns = []

        for ticker in top["Ticker"]:
            df = data[ticker]
            try:
                start_price = df.loc[start]["Close"]
                end_price = df.loc[end]["Close"]
                r = (end_price / start_price) - 1
                period_returns.append(r)
            except:
                continue

        if len(period_returns) == 0:
            continue

        portfolio_returns.append(sum(period_returns) / len(period_returns))

    return pd.Series(portfolio_returns).cumsum()
