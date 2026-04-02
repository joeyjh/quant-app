import pandas as pd
import streamlit as st
import yfinance as yf

from config import TOP_N
from data import get_sp500, load_all_data, get_fundamentals, get_chart
from factors import calculate_factors, calculate_scores, backtest_strategy
from metrics import calculate_cagr, calculate_sharpe, calculate_mdd


st.write("버전3 - 미국주식")
st.title("📈 Quant Stock Recommender (US Market)")


tickers = get_sp500()

momentum_weight = st.sidebar.slider("Momentum", 0.0, 1.0, 0.4)
risk_weight = st.sidebar.slider("Risk", 0.0, 1.0, 0.3)
value_weight = st.sidebar.slider("Value", 0.0, 1.0, 0.3)
quality_weight = st.sidebar.slider("Quality", 0.0, 1.0, 0.2)

total = momentum_weight + risk_weight + value_weight + quality_weight

if total > 0:
    momentum_weight /= total
    risk_weight /= total
    value_weight /= total
    quality_weight /= total


with st.spinner("📊 DB 데이터 로딩 중..."):
    data = load_all_data(tickers)
    fundamentals = get_fundamentals(tickers)

if len(tickers) == 0:
    st.error("S&P500 종목 리스트를 불러오지 못했습니다.")
    st.stop()

if len(data) == 0:
    st.error("가격 데이터가 없습니다. 먼저 'py update_db.py'를 실행해서 DB를 생성해 주세요.")
    st.stop()

df = calculate_factors(data, fundamentals, tickers)

df["return"] = pd.to_numeric(df["return"], errors="coerce")
df["volatility"] = pd.to_numeric(df["volatility"], errors="coerce")

df = df.dropna().reset_index(drop=True)

if len(df) == 0:
    st.warning("데이터가 부족합니다.")
    st.stop()

weights = (momentum_weight, risk_weight, value_weight, quality_weight)
df = calculate_scores(df, weights)

df["return"] = df["return"].round(4)
df["volatility"] = df["volatility"].round(4)
df["value"] = df["value"].round(4)
df["quality"] = df["quality"].round(4)
df["score"] = df["score"].round(2)

df = df.rename(columns={
    "return": "Return (6M)",
    "volatility": "Risk (Vol)",
    "value": "Value Score",
    "quality": "Quality Score",
    "score": "Total Score"
})

st.subheader("🏆 추천 종목 TOP 10")

top10 = df.head(TOP_N).copy()

top10["Company"] = top10["Ticker"].apply(
    lambda x: fundamentals.get(x, {}).get("name", x)
)

top10["Display"] = top10["Company"] + " (" + top10["Ticker"] + ")"

st.dataframe(
    top10[
        ["Display", "Return (6M)", "Risk (Vol)", "Value Score", "Quality Score", "Total Score"]
    ].rename(columns={"Display": "Company"})
)

selected_display = st.selectbox(
    "📊 종목 선택",
    top10["Display"]
)

selected_ticker = top10[
    top10["Display"] == selected_display
]["Ticker"].values[0]

chart_data = get_chart(selected_ticker)

st.subheader(f"📈 {selected_ticker} 가격 차트")
if chart_data is not None and not chart_data.empty:
    st.line_chart(chart_data["Close"])
else:
    st.warning("차트 데이터가 없습니다.")

st.subheader("📊 백테스트 결과")

bt, turnovers = backtest_strategy(data, fundamentals, tickers, weights)

if bt is not None and len(bt) > 0:
    st.line_chart(bt)

    if len(turnovers) > 0:
        avg_turnover = sum(turnovers) / len(turnovers)
        st.write(f"🔁 Average Turnover: {avg_turnover:.2%}")
    else:
        st.write("🔁 Turnover 데이터 부족")

    spy = yf.download("SPY", period="2y", progress=False)
    if spy is not None and not spy.empty:
        spy_returns = spy["Close"].pct_change().dropna().squeeze()
        spy_cum = spy_returns.cumsum()

        min_len = min(len(bt), len(spy_cum))

        compare_df = pd.DataFrame({
            "Strategy": bt.values.flatten()[:min_len],
            "S&P500": spy_cum.values.flatten()[:min_len]
        })

        st.subheader("📊 전략 vs S&P500")
        st.line_chart(compare_df)

    cagr = calculate_cagr(bt)
    if cagr is not None:
        st.write(f"📈 CAGR: {cagr:.2%}")

    sharpe = calculate_sharpe(bt)
    if sharpe is not None:
        st.write(f"📊 Sharpe Ratio: {sharpe:.2f}")

    mdd = calculate_mdd(bt)
    if mdd is not None:
        st.write(f"📉 Max Drawdown: {mdd:.2%}")
else:
    st.warning("백테스트 데이터 부족")
