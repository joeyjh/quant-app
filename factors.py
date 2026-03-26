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