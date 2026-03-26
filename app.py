import yfinance as yf
import pandas as pd
import streamlit as st

from data import get_sp500, load_all_data, get_fundamentals, get_chart
from factors import calculate_factors, calculate_scores


st.write("버전2 - 미국주식")
st.title("📈 Quant Stock Recommender (US Market)")


tickers = get_sp500()[:100]  # 🔥 100개만 사용 (안정성)

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