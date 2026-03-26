import streamlit as st
import pandas as pd
import yfinance as yf

st.title("📈 Quant Stock Recommender (US Market)")

# 🥇 S&P500 종목 가져오기
@st.cache_data
def get_sp500():
    url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
    table = pd.read_html(url)[0]
    return table["Symbol"].tolist()

tickers = get_sp500()[:100]  # 🔥 100개만 사용 (안정성)

# 🎯 슬라이더 (가중치)
momentum_weight = st.sidebar.slider("Momentum", 0.0, 1.0, 0.4)
risk_weight = st.sidebar.slider("Risk", 0.0, 1.0, 0.3)
value_weight = st.sidebar.slider("Value", 0.0, 1.0, 0.3)

# 🔄 정규화
total = momentum_weight + risk_weight + value_weight
if total > 0:
    momentum_weight /= total
    risk_weight /= total
    value_weight /= total

# 🥇 데이터 가져오기 함수 (캐싱)
@st.cache_data
def load_data(ticker):
    try:
        df = yf.download(ticker, period="6mo")
        return df
    except:
        return None

results = []

# 📊 데이터 수집
for ticker in tickers:
    df = load_data(ticker)

    if df is None or df.empty:
        continue

    try:
        # 📈 모멘텀
        ret = df['Close'].pct_change(120).iloc[-1]

        # 📉 리스크
        vol = df['Close'].pct_change().std()

        # 💰 밸류 (간단 proxy)
        value = 1 / df['Close'].iloc[-1]

        results.append({
            "Ticker": ticker,
            "return": ret,
            "volatility": vol,
            "value": value
        })

    except:
        continue

df = pd.DataFrame(results)

# 🧠 결과 처리
if df.empty:
    st.warning("데이터를 불러오지 못했습니다.")
else:
    # 📊 랭킹 계산
    df["momentum_rank"] = df["return"].rank(ascending=False)
    df["risk_rank"] = df["volatility"].rank(ascending=True)
    df["value_rank"] = df["value"].rank(ascending=False)

    # 🎯 최종 점수
    df["score"] = (
        df["momentum_rank"] * momentum_weight +
        df["risk_rank"] * risk_weight +
        df["value_rank"] * value_weight
    )

    df = df.sort_values("score")

    st.subheader("🏆 추천 종목 TOP 10")
    st.dataframe(df.head(10)[["Ticker", "score"]])
