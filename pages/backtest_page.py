import pandas as pd
import streamlit as st
import yfinance as yf

from chart_utils import make_backtest_chart, make_compare_chart
from metrics import calculate_cagr, calculate_mdd, calculate_sharpe
from state_utils import PERIOD_OPTIONS
from ui_utils import apply_period_filter, metric_text


def render_backtest_page(data, fundamentals, tickers, weights, backtest_strategy):
    st.markdown("## 백테스트")
    st.caption("현재 선택한 preset 기준으로, 월 1회 리밸런싱했을 때의 누적 수익률 변화를 확인합니다.")

    selected_preset = st.session_state.get("selected_preset", "기본 추천")
    momentum_w, risk_w, value_w, quality_w = weights

    st.info(
        f"현재 백테스트 기준 전략: **{selected_preset}**  \n"
        f"- Momentum: **{momentum_w:.0%}**  \n"
        f"- Risk: **{risk_w:.0%}**  \n"
        f"- Value: **{value_w:.0%}**  \n"
        f"- Quality: **{quality_w:.0%}**"
    )

    s1, s2, s3 = st.columns(3)
    s1.metric("현재 Preset", selected_preset)
    s2.metric("리밸런싱 주기", "월 1회")
    s3.metric("포트폴리오 수", "10종목")

    bt, turnovers = backtest_strategy(data, fundamentals, tickers, weights)

    avg_turnover = None
    if len(turnovers) > 0:
        avg_turnover = sum(turnovers) / len(turnovers)

    cagr = calculate_cagr(bt)
    sharpe = calculate_sharpe(bt)
    mdd = calculate_mdd(bt)

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("CAGR", metric_text(cagr, "percent", 2))
    m2.metric("Sharpe", metric_text(sharpe, "float", 2))
    m3.metric("MDD", metric_text(mdd, "percent", 2))
    m4.metric("평균 Turnover", metric_text(avg_turnover, "percent", 1))

    st.info("백테스트는 과거 데이터 기준으로, 이 전략을 매달 리밸런싱하며 운용했을 때의 성과를 보여줍니다. 미래 수익을 보장하지는 않지만 전략의 성격을 이해하는 데 도움을 줍니다.")

    st.markdown("### 차트 기간 선택")
    st.radio(
        "백테스트 기간",
        list(PERIOD_OPTIONS.keys()),
        horizontal=True,
        key="backtest_period_label"
    )

    if bt is not None and len(bt) > 0:
        bt_filtered = apply_period_filter(bt, st.session_state["backtest_period_label"], PERIOD_OPTIONS)

        st.markdown("### 내 전략의 누적 수익률")
        st.caption("이 그래프는 시간이 지날수록 내 전략의 수익률이 얼마나 누적되었는지를 보여줍니다. x축은 날짜, y축은 누적 수익률(%)입니다.")
        st.plotly_chart(make_backtest_chart(bt_filtered), use_container_width=True)

        spy = yf.download("SPY", period="2y", progress=False)
        if spy is not None and not spy.empty:
            spy_returns = spy["Close"].pct_change().dropna().squeeze()
            spy_cum = spy_returns.cumsum()

            compare_df = pd.DataFrame({
                "Strategy": bt.values.flatten(),
                "S&P500": spy_cum.values.flatten()[:len(bt)] if len(spy_cum) >= len(bt) else list(spy_cum.values.flatten()) + [None] * (len(bt) - len(spy_cum))
            }, index=bt.index)

            compare_df = compare_df.dropna()
            compare_df = apply_period_filter(compare_df, st.session_state["backtest_period_label"], PERIOD_OPTIONS)

            st.markdown("### 내 전략 vs S&P500")
            st.caption("내 전략과 시장(S&P500)의 누적 수익률을 비교한 그래프입니다. x축은 날짜, y축은 누적 수익률(%)입니다.")
            st.plotly_chart(make_compare_chart(compare_df), use_container_width=True)
    else:
        st.warning("백테스트 데이터가 부족합니다.")