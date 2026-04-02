import pandas as pd
import streamlit as st
import yfinance as yf

from config import TOP_N
from data import get_sp500, load_all_data, get_fundamentals, get_chart
from factors import (
    calculate_factors,
    calculate_scores,
    backtest_strategy,
    select_portfolio_with_buffer,
)
from metrics import calculate_cagr, calculate_sharpe, calculate_mdd


PRESETS = {
    "직접 설정": None,
    "기본 추천": {
        "momentum": 0.35,
        "risk": 0.25,
        "value": 0.20,
        "quality": 0.20,
        "description": "가장 기본이 되는 추천 비중입니다. 모멘텀을 중심으로 두되, 리스크·밸류·퀄리티를 함께 반영해 과도한 쏠림을 줄인 균형형 구조입니다."
    },
    "추세형": {
        "momentum": 0.40,
        "risk": 0.20,
        "value": 0.20,
        "quality": 0.20,
        "description": "추세를 조금 더 강하게 반영하는 비중입니다. 상승 흐름을 더 중시하지만, 밸류와 퀄리티를 완전히 포기하지 않도록 유지한 형태입니다."
    },
    "안정형": {
        "momentum": 0.25,
        "risk": 0.35,
        "value": 0.20,
        "quality": 0.20,
        "description": "월 1회 운용에서 변동성 억제를 더 중시하는 비중입니다. 리스크 관리를 강화해 포트폴리오 교체와 흔들림을 줄이는 데 초점을 둡니다."
    }
}


def apply_preset_if_changed():
    current_preset = st.session_state.get("preset_select", "기본 추천")
    last_preset = st.session_state.get("last_preset", None)

    if current_preset != last_preset:
        preset = PRESETS.get(current_preset)

        if preset is not None:
            st.session_state["momentum_weight"] = preset["momentum"]
            st.session_state["risk_weight"] = preset["risk"]
            st.session_state["value_weight"] = preset["value"]
            st.session_state["quality_weight"] = preset["quality"]

        st.session_state["last_preset"] = current_preset


def parse_holdings(text):
    if not text:
        return []

    items = [x.strip().upper() for x in text.replace("\n", ",").split(",")]
    items = [x for x in items if x]

    # 중복 제거 + 순서 유지
    seen = set()
    result = []
    for item in items:
        if item not in seen:
            seen.add(item)
            result.append(item)

    return result


def enrich_portfolio_table(df_portfolio, fundamentals):
    table = df_portfolio.copy()

    table["Company"] = table["Ticker"].apply(
    lambda x: fundamentals.get(x, {}).get("name", x)
    )
    table["Company"] = table["Company"] + " (" + table["Ticker"] + ")"

    table["momentum"] = table["momentum"].round(4)
    table["volatility"] = table["volatility"].round(4)
    table["value"] = table["value"].round(4)
    table["quality"] = table["quality"].round(4)
    table["score"] = table["score"].round(3)

    table = table.rename(columns={
        "momentum": "Momentum (12-1M)",
        "volatility": "Risk (Vol)",
        "value": "Value Score",
        "quality": "Quality Score",
        "score": "Total Score"
    })

    return table


st.write("버전6 - 미국주식")
st.title("📈 Quant Stock Recommender (US Market)")

tickers = get_sp500()

if "momentum_weight" not in st.session_state:
    st.session_state["momentum_weight"] = 0.35
if "risk_weight" not in st.session_state:
    st.session_state["risk_weight"] = 0.25
if "value_weight" not in st.session_state:
    st.session_state["value_weight"] = 0.20
if "quality_weight" not in st.session_state:
    st.session_state["quality_weight"] = 0.20
if "last_preset" not in st.session_state:
    st.session_state["last_preset"] = None
if "preset_select" not in st.session_state:
    st.session_state["preset_select"] = "기본 추천"

st.sidebar.subheader("⚙️ 투자 스타일 선택")

st.sidebar.selectbox(
    "Preset",
    list(PRESETS.keys()),
    key="preset_select"
)

apply_preset_if_changed()

is_manual = st.session_state["preset_select"] == "직접 설정"

momentum_weight = st.sidebar.slider(
    "Momentum",
    0.0, 1.0,
    float(st.session_state["momentum_weight"]),
    key="momentum_weight",
    disabled=not is_manual
)
risk_weight = st.sidebar.slider(
    "Risk",
    0.0, 1.0,
    float(st.session_state["risk_weight"]),
    key="risk_weight",
    disabled=not is_manual
)
value_weight = st.sidebar.slider(
    "Value",
    0.0, 1.0,
    float(st.session_state["value_weight"]),
    key="value_weight",
    disabled=not is_manual
)
quality_weight = st.sidebar.slider(
    "Quality",
    0.0, 1.0,
    float(st.session_state["quality_weight"]),
    key="quality_weight",
    disabled=not is_manual
)

total = momentum_weight + risk_weight + value_weight + quality_weight

if total > 0:
    momentum_weight /= total
    risk_weight /= total
    value_weight /= total
    quality_weight /= total

weights = (momentum_weight, risk_weight, value_weight, quality_weight)

st.sidebar.markdown("### 현재 반영 비중")
st.sidebar.write(f"Momentum: {momentum_weight:.0%}")
st.sidebar.write(f"Risk: {risk_weight:.0%}")
st.sidebar.write(f"Value: {value_weight:.0%}")
st.sidebar.write(f"Quality: {quality_weight:.0%}")

if not is_manual:
    selected_preset = PRESETS[st.session_state["preset_select"]]
    st.sidebar.info(selected_preset["description"])
else:
    st.sidebar.info("직접 설정에서는 슬라이더로 4개 팩터 비중을 자유롭게 조정할 수 있습니다.")

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

df["momentum"] = pd.to_numeric(df["momentum"], errors="coerce")
df["volatility"] = pd.to_numeric(df["volatility"], errors="coerce")

df = df.dropna().reset_index(drop=True)

if len(df) == 0:
    st.warning("데이터가 부족합니다.")
    st.stop()

scored_df = calculate_scores(df, weights)

st.markdown("### 🧭 투자 철학")
st.markdown(
    """
이 앱은 **과최적화를 피하면서 월 1회 리밸런싱에 활용할 수 있는 단순 4팩터 모델**을 목표로 합니다.

- **Momentum**: 최근 1개월을 제외한 12개월 추세를 반영합니다.
- **Risk**: 최근 6개월 변동성을 반영합니다.
- **Value**: 낮은 PER 기업을 선호합니다.
- **Quality**: 이익률이 좋은 기업을 선호합니다.

기본 철학은 **모멘텀을 중심으로 두되, 리스크·밸류·퀄리티를 함께 섞어 한 가지 스타일에 과도하게 쏠리지 않게 만드는 것**입니다.
"""
)

if not is_manual:
    preset_name = st.session_state["preset_select"]
    st.markdown(f"### 📌 현재 선택된 Preset: {preset_name}")
    st.write(PRESETS[preset_name]["description"])
else:
    st.markdown("### 📌 현재 선택된 Preset: 직접 설정")
    st.write("슬라이더를 이용해 자신이 중요하다고 생각하는 팩터 비중을 직접 조정할 수 있습니다.")

# =========================
# 월간 리밸런싱 입력
# =========================
st.subheader("🗓️ 월간 리밸런싱 실행")
st.caption("지난달 보유 종목을 입력하면 이번 달 기준으로 유지 / 신규편입 / 제외 종목을 자동으로 계산합니다. 입력이 없으면 현재 점수 상위 10종목을 기준으로 보여줍니다.")

previous_holdings_text = st.text_area(
    "지난달 보유 종목 티커 입력 (쉼표로 구분, 예: AAPL, MSFT, NVDA)",
    value="",
    height=100
)

previous_holdings = parse_holdings(previous_holdings_text)
valid_previous_holdings = [x for x in previous_holdings if x in scored_df["Ticker"].tolist()]

if previous_holdings and not valid_previous_holdings:
    st.warning("입력한 종목 중 현재 평가 가능한 종목이 없습니다. 현재 점수 상위 종목 기준으로 보여줍니다.")

portfolio_df = select_portfolio_with_buffer(
    scored_df,
    valid_previous_holdings,
    top_n=TOP_N,
    buffer_n=15
)

final_holdings = portfolio_df["Ticker"].tolist()
kept_holdings = [x for x in final_holdings if x in valid_previous_holdings]
new_holdings = [x for x in final_holdings if x not in valid_previous_holdings]
removed_holdings = [x for x in valid_previous_holdings if x not in final_holdings]

target_weight = 1 / TOP_N if TOP_N > 0 else 0

st.markdown("### ✅ 이번 달 최종 매수 후보")
st.write(f"동일가중 기준 종목당 목표 비중: **{target_weight:.0%}**")

portfolio_table = enrich_portfolio_table(portfolio_df, fundamentals)
st.dataframe(
    portfolio_table[
        ["Company", "Momentum (12-1M)", "Risk (Vol)", "Value Score", "Quality Score", "Total Score"]
    ]
)

col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("#### 🔒 계속 보유")
    if kept_holdings:
        for ticker in kept_holdings:
            name = fundamentals.get(ticker, {}).get("name", ticker)
            st.write(f"- {name} ({ticker})")
    else:
        st.write("해당 없음")

with col2:
    st.markdown("#### 🟢 신규 편입")
    if new_holdings:
        for ticker in new_holdings:
            name = fundamentals.get(ticker, {}).get("name", ticker)
            st.write(f"- {name} ({ticker})")
    else:
        st.write("해당 없음")

with col3:
    st.markdown("#### 🔴 제외")
    if removed_holdings:
        for ticker in removed_holdings:
            name = fundamentals.get(ticker, {}).get("name", ticker)
            st.write(f"- {name} ({ticker})")
    else:
        st.write("해당 없음")

st.markdown("### 🏆 현재 점수 기준 상위 10종목")
st.caption("아래 표는 순수 점수 기준 상위 10종목입니다. 실제 월간 운용은 위의 최종 매수 후보 표를 참고하면 됩니다.")

top10 = scored_df.head(TOP_N).copy()
top10_table = enrich_portfolio_table(top10, fundamentals)

st.dataframe(
    top10_table[
        ["Company", "Momentum (12-1M)", "Risk (Vol)", "Value Score", "Quality Score", "Total Score"]
    ]
)

selected_source = st.radio(
    "차트/상세 확인 기준",
    ["이번 달 최종 매수 후보", "현재 점수 기준 상위 10종목"],
    horizontal=True
)

if selected_source == "이번 달 최종 매수 후보":
    selectable_table = portfolio_table.copy()
else:
    selectable_table = top10_table.copy()

selected_company = st.selectbox(
    "📊 종목 선택",
    selectable_table["Company"]
)

selected_ticker = selected_company.split("(")[-1].replace(")", "").strip()
chart_data = get_chart(selected_ticker)

st.subheader(f"📈 {selected_ticker} 가격 차트")
if chart_data is not None and not chart_data.empty:
    st.line_chart(chart_data["Close"])
else:
    st.warning("차트 데이터가 없습니다.")

st.subheader("📊 백테스트 결과")
st.caption("백테스트에는 buffer rule이 반영됩니다. 기존 보유 종목이 일정 순위 안에 남아 있으면 유지해 월간 운용에 더 적합하게 설계했습니다.")

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