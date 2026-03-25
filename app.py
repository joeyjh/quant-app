import streamlit as st
import FinanceDataReader as fdr
import pandas as pd
import numpy as np

st.title("📊 퀀트 주식 추천 앱")

st.sidebar.header("⚙️ 설정")

momentum_weight = st.sidebar.slider("Momentum", 0.0, 1.0, 0.4)
risk_weight = st.sidebar.slider("Risk", 0.0, 1.0, 0.3)
value_weight = st.sidebar.slider("Value", 0.0, 1.0, 0.3)

total = momentum_weight + risk_weight + value_weight

if total > 0:
    momentum_weight /= total
    risk_weight /= total
    value_weight /= total

selected_sector = st.sidebar.selectbox(
    "산업 선택",
    ["전체", "반도체", "자동차", "금융"]
)


# 종목 리스트 가져오기
try:
    stocks = fdr.StockListing('KOSDAQ').head(30)
except:
    st.warning("데이터 서버 상태가 불안정합니다. 다시 시도해주세요.")
    st.stop()
# 임시 산업 데이터 (테스트용)
stocks["sector"] = ["반도체", "자동차", "금융", "반도체", "자동차"] * 10

# 산업 필터 적용
if selected_sector != "전체":
    stocks = stocks[stocks["sector"] == selected_sector]

results = []

for code, name in zip(stocks['Code'], stocks['Name']):

    # 1. 데이터 가져오기
    try:
        price = fdr.DataReader(code)
        if price.empty:
            continue
    except:
        continue

    # 2. 계산
    try:
        ret = price['Close'].pct_change(120).iloc[-1]
        vol = price['Close'].pct_change().std()
    except:
        continue

    # 3. 결과 저장
    results.append({
        "종목": name,
        "return": ret,
        "volatility": vol
    })

df = pd.DataFrame(results)

# NaN 제거
df = df.dropna()
# 🔥 Value 데이터 추가 (여기!)
df["PER"] = np.random.uniform(5, 30, len(df))
df["PBR"] = np.random.uniform(0.5, 5, len(df))

# 점수 계산
df["momentum_rank"] = df["return"].rank(ascending=False)
df["risk_rank"] = df["volatility"].rank(ascending=True)

# 🔥 Value rank 추가
df["per_rank"] = df["PER"].rank(ascending=True)
df["pbr_rank"] = df["PBR"].rank(ascending=True)

df["value_score"] = (df["per_rank"] + df["pbr_rank"]) / 2

df["score"] = (
    df["momentum_rank"] * momentum_weight +
    df["risk_rank"] * risk_weight +
    df["value_score"] * value_weight
)
# 정렬
df = df.sort_values("score")

# 출력
st.subheader("🏆 추천 종목 TOP 10")
st.dataframe(df.head(10))
