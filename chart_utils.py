import plotly.graph_objects as go


def make_price_chart(df, ticker):
    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df["Close"],
            mode="lines",
            name=ticker,
        )
    )

    fig.update_layout(
        title=f"{ticker} Price Chart",
        xaxis_title="날짜",
        yaxis_title="종가",
        height=420,
        margin=dict(l=20, r=20, t=50, b=20),
        uirevision=f"price-{ticker}",
    )

    return fig


def make_backtest_chart(bt):
    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=bt.index,
            y=bt.values * 100,
            mode="lines",
            name="내 전략",
        )
    )

    fig.update_layout(
        title="내 전략의 누적 수익률 변화",
        xaxis_title="날짜",
        yaxis_title="누적 수익률 (%)",
        height=420,
        margin=dict(l=20, r=20, t=50, b=20),
        uirevision="backtest-main",
    )

    return fig


def make_compare_chart(compare_df):
    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=compare_df.index,
            y=compare_df["Strategy"] * 100,
            mode="lines",
            name="내 전략",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=compare_df.index,
            y=compare_df["S&P500"] * 100,
            mode="lines",
            name="S&P500",
        )
    )

    fig.update_layout(
        title="내 전략과 S&P500 누적 수익률 비교",
        xaxis_title="날짜",
        yaxis_title="누적 수익률 (%)",
        height=420,
        margin=dict(l=20, r=20, t=50, b=20),
        uirevision="backtest-compare",
    )

    return fig