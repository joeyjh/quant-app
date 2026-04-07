import pandas as pd
import streamlit as st

from data import get_chart, get_fundamentals, get_sp500, load_all_data
from factors import backtest_strategy, calculate_factors, calculate_scores
from pages.backtest_page import render_backtest_page
from pages.chart_page import render_price_chart_page
from pages.home_page import render_home_page
from pages.mock_page import render_mock_page
from pages.settings_page import render_settings_page
from pages.strategy_page import render_strategy_page
from state_utils import PAGES, get_normalized_weights, init_session_state


st.set_page_config(
    page_title="Quant Stock Recommender",
    page_icon="📈",
    layout="wide"
)


def render_top_navigation():
    st.markdown(
        """
        <style>
        .block-container {
            max-width: 1100px;
            padding-top: 1.2rem;
            padding-bottom: 2rem;
        }
        .hero-box {
            padding: 1.2rem 1.2rem 1rem 1.2rem;
            border-radius: 18px;
            border: 1px solid rgba(128,128,128,0.18);
            background: rgba(255,255,255,0.02);
            margin-bottom: 1rem;
        }
        </style>
        """,
        unsafe_allow_html=True
    )

    st.markdown('<div class="hero-box">', unsafe_allow_html=True)
    st.markdown("### 📈 Quant Stock Recommender")
    st.caption("월 1회 리밸런싱을 위한 미국주식 추천 앱")
    st.markdown('</div>', unsafe_allow_html=True)

    page = st.radio(
        "메뉴",
        PAGES,
        horizontal=True,
        key="selected_page",
        label_visibility="collapsed"
    )

    return page


def load_model_data():
    tickers = get_sp500()

    with st.spinner("📊 데이터를 불러오는 중..."):
        data = load_all_data(tickers)
        fundamentals = get_fundamentals(tickers)

    if len(tickers) == 0:
        st.error("S&P500 종목 리스트를 불러오지 못했습니다.")
        st.stop()

    if len(data) == 0:
        st.error("가격 데이터가 없습니다. 먼저 'py update_db.py'를 실행해 주세요.")
        st.stop()

    df = calculate_factors(data, fundamentals, tickers)

    if df is None or len(df) == 0:
        st.warning("평가 가능한 데이터가 부족합니다.")
        st.stop()

    df["momentum"] = pd.to_numeric(df["momentum"], errors="coerce")
    df["volatility"] = pd.to_numeric(df["volatility"], errors="coerce")
    df = df.dropna().reset_index(drop=True)

    if len(df) == 0:
        st.warning("평가 가능한 데이터가 부족합니다.")
        st.stop()

    weights = get_normalized_weights()
    scored_df = calculate_scores(df, weights)

    return tickers, data, fundamentals, scored_df, weights


init_session_state()
page = render_top_navigation()

needs_model_data = page in ["홈", "백테스트", "가격차트", "모의투자"]

if needs_model_data:
    tickers, data, fundamentals, scored_df, weights = load_model_data()

    if page == "홈":
        render_home_page(fundamentals, scored_df)
    elif page == "백테스트":
        render_backtest_page(data, fundamentals, tickers, weights, backtest_strategy)
    elif page == "가격차트":
        render_price_chart_page(fundamentals, scored_df, get_chart)
    elif page == "모의투자":
        render_mock_page(fundamentals, scored_df, weights)
elif page == "전략":
    render_strategy_page()
elif page == "설정":
    render_settings_page()