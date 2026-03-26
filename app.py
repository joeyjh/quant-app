import streamlit as st
import pandas as pd
import yfinance as yf
import requests
st.write("버전2 - 미국주식")
st.title("📈 Quant Stock Recommender (US Market)")

# 🥇 S&P500 종목 가져오기
@st.cache_data
def get_sp500():
    url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
    
    headers = {
        "User-Agent": "Mozilla/5.0"
    }
    
    response = requests.get(url, headers=headers)
    tables = pd.read_html(response.text)
    
    return tables[0]["Symbol"].tolist()

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


@st.cache_data(ttl=3600)
def load_all_data(tickers):
    return yf.download(
        tickers,
        period="6mo",
        group_by='ticker',
        threads=True,
        progress=False
    )

data = load_all_data(tickers)

results = []


for ticker in tickers:
    try:
        df = data[ticker]

        if df is None or df.empty:
            continue

        # 모멘텀
        ret = df['Close'].pct_change(120).iloc[-1]

        if pd.isna(ret):
            continue

        # 리스크
        vol = df['Close'].pct_change().std()

        # 밸류
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
