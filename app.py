
import pandas as pd
import streamlit as st
import yfinance as yf

from data import get_sp500, load_all_data, get_fundamentals, get_chart
from factors import calculate_factors, calculate_scores
from factors import backtest_strategy


st.write("버전2 - 미국주식")
st.title("📈 Quant Stock Recommender (US Market)")


tickers = get_sp500() # 🔥 100개만 사용 (안정성)
st.write("Ticker count:", len(tickers))

# 🎯 슬라이더 (가중치)
momentum_weight = st.sidebar.slider("Momentum", 0.0, 1.0, 0.4)
risk_weight = st.sidebar.slider("Risk", 0.0, 1.0, 0.3)
value_weight = st.sidebar.slider("Value", 0.0, 1.0, 0.3)
quality_weight = st.sidebar.slider("Quality", 0.0, 1.0, 0.2)

# 🔄 정규화
total = momentum_weight + risk_weight + value_weight + quality_weight

if total > 0:
    momentum_weight /= total
    risk_weight /= total
    value_weight /= total
    quality_weight /= total


with st.spinner("📊 데이터 로딩 중... (최초 1회 약 1~2분 소요)"):
    data = load_all_data(tickers)
    fundamentals = get_fundamentals(tickers)

df = calculate_factors(data, fundamentals, tickers)


# 🔥 타입 강제 변환
df["return"] = pd.to_numeric(df["return"], errors="coerce")
df["volatility"] = pd.to_numeric(df["volatility"], errors="coerce")

# 🔥 데이터 정리
df = df.dropna()
df = df.reset_index(drop=True)

# 🔥 빈 데이터 방지
if len(df) == 0:
    st.warning("데이터가 부족합니다.")
    st.stop()

# 🧠 결과 처리
if df.empty:
    st.warning("데이터를 불러오지 못했습니다.")
else:
    # 📊 랭킹 계산
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

top10 = df.head(10).copy()

top10["Company"] = top10["Ticker"].apply(
    lambda x: fundamentals.get(x, {}).get("name", x)
)

top10["Display"] = top10["Company"] + " (" + top10["Ticker"] + ")"

#데이터 프레임 출력
st.dataframe(
    top10[
        ["Display", "Return (6M)", "Risk (Vol)", "Value Score", "Quality Score", "Total Score"]
    ].rename(columns={"Display": "Company"})
)
# 🟢 종목 선택
selected_display = st.selectbox(
    "📊 종목 선택",
    top10["Display"]
)

selected_ticker = top10[
    top10["Display"] == selected_display
]["Ticker"].values[0]
# 🟢 차트 데이터 가져오기 (캐싱 적용)
chart_data = get_chart(selected_ticker)

# 🟢 차트 출력
st.subheader(f"📈 {selected_ticker} 가격 차트")
st.line_chart(chart_data["Close"])


# 백테스트
st.subheader("📊 백테스트 결과")

weights = (momentum_weight, risk_weight, value_weight, quality_weight)

bt, turnovers = backtest_strategy(data, fundamentals, tickers, weights)

if bt is not None and len(bt) > 0:
    st.line_chart(bt)
    
    # 🔁 turnover 출력 (여기!)
    if len(turnovers) > 0:
        avg_turnover = sum(turnovers) / len(turnovers)
        st.write(f"🔁 Average Turnover: {avg_turnover:.2%}")
    else:
        st.write("🔁 Turnover 데이터 부족")
    

    # ===== 여기부터 추가 =====

    # 📊 S&P500
    spy = yf.download("SPY", period="2y", progress=False)
    spy_returns = spy["Close"].pct_change().dropna().squeeze()
    spy_cum = spy_returns.cumsum()

    # 길이 맞추기
    min_len = min(len(bt), len(spy_cum))

    compare_df = pd.DataFrame({
        "Strategy": bt.values.flatten()[:min_len],
        "S&P500": spy_cum.values.flatten()[:min_len]
    })

    st.subheader("📊 전략 vs S&P500")
    st.line_chart(compare_df)

    # 📈 CAGR
    years = len(bt) / 12
    total_return = bt.iloc[-1]
    cagr = (1 + total_return) ** (1 / years) - 1
    st.write(f"📈 CAGR: {cagr:.2%}")

    # 📊 Sharpe Ratio
    returns = bt.diff().dropna()
    sharpe = returns.mean() / returns.std() * (12 ** 0.5)
    st.write(f"📊 Sharpe Ratio: {sharpe:.2f}")

    # 📉 MDD
    cum = (1 + returns).cumprod()
    peak = cum.cummax()
    drawdown = (cum - peak) / peak
    mdd = drawdown.min()
    st.write(f"📉 Max Drawdown: {mdd:.2%}")

    # ===== 여기까지 추가 =====

else:
    st.warning("백테스트 데이터 부족")

