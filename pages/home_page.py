import streamlit as st

from config import TOP_N
from factors import select_portfolio_with_buffer
from state_utils import (
    PRESETS,
    apply_current_strategy,
    apply_preset_if_changed,
    get_draft_normalized_weights,
    get_normalized_weights,
    is_strategy_dirty,
)
from ui_utils import enrich_table, format_ticker_list, metric_text, parse_holdings

def render_stock_card(row, fundamentals):
    ticker = row["Ticker"]
    company = fundamentals.get(ticker, {}).get("name", ticker)

    momentum = row["momentum"]
    risk = row["volatility"]
    value = row["value"]
    quality = row["quality"]
    total_score = row["score"]

    # 점수 뱃지용 간단 등급
    if total_score >= 0.80:
        badge_label = "Top"
    elif total_score >= 0.65:
        badge_label = "High"
    else:
        badge_label = "Good"

    with st.container(border=True):
        left, mid, right = st.columns([6, 2, 1])

        with left:
            st.markdown(f"**{company}**")
            st.caption(ticker)

        with mid:
            st.markdown(
                f"""
                <div style="
                    display:inline-block;
                    padding:6px 10px;
                    border-radius:999px;
                    background:rgba(255,255,255,0.08);
                    border:1px solid rgba(255,255,255,0.12);
                    font-size:12px;
                    font-weight:600;
                    text-align:center;
                    min-width:76px;
                ">
                    {badge_label} · {total_score:.3f}
                </div>
                """,
                unsafe_allow_html=True
            )

        with right:
            st.markdown(
                f"""
                <div style="
                    width:36px;
                    height:36px;
                    border-radius:50%;
                    display:flex;
                    align-items:center;
                    justify-content:center;
                    background:rgba(255,255,255,0.08);
                    border:1px solid rgba(255,255,255,0.12);
                    font-weight:700;
                    font-size:14px;
                    margin-left:auto;
                ">
                    {ticker[0]}
                </div>
                """,
                unsafe_allow_html=True
            )

        with st.expander("점수 보기", expanded=False):
            c1, c2 = st.columns(2)
            with c1:
                st.write(f"**Momentum**: {momentum:.4f}")
                st.write(f"**Value**: {value:.4f}")
            with c2:
                st.write(f"**Risk**: {risk:.4f}")
                st.write(f"**Quality**: {quality:.4f}")

            st.write(f"**Total Score:** {total_score:.3f}")

def render_stock_cards(df, fundamentals, limit=10):
    subset = df.head(limit).copy()

    for _, row in subset.iterrows():
        render_stock_card(row, fundamentals)


def render_home_page(fundamentals, scored_df):
    st.markdown("## 홈")
    st.caption("먼저 투자 스타일을 고르고, 전략을 고정한 뒤 추천 결과를 확인합니다.")

    st.markdown("### 1) 전략 선택")

    selected_preset = st.radio(
        "투자 스타일",
        list(PRESETS.keys()),
        horizontal=True,
        key="selected_preset"
    )

    apply_preset_if_changed()

    preset = PRESETS[selected_preset]
    st.info(f"선택 중인 전략: **{selected_preset}** — {preset['description']}")

    is_manual = selected_preset == "직접 설정"

    if is_manual:
        st.markdown("### 직접 비중 조정")
        col1, col2 = st.columns(2)

        with col1:
            st.slider("Momentum", 0.0, 1.0, float(st.session_state["momentum_weight"]), key="momentum_weight")
            st.slider("Risk", 0.0, 1.0, float(st.session_state["risk_weight"]), key="risk_weight")

        with col2:
            st.slider("Value", 0.0, 1.0, float(st.session_state["value_weight"]), key="value_weight")
            st.slider("Quality", 0.0, 1.0, float(st.session_state["quality_weight"]), key="quality_weight")

    draft_weights = get_draft_normalized_weights()
    applied_weights = get_normalized_weights()

    st.markdown("#### 현재 선택 중인 비중")
    w1, w2, w3, w4 = st.columns(4)
    w1.metric("Momentum", metric_text(draft_weights[0], "percent", 0))
    w2.metric("Risk", metric_text(draft_weights[1], "percent", 0))
    w3.metric("Value", metric_text(draft_weights[2], "percent", 0))
    w4.metric("Quality", metric_text(draft_weights[3], "percent", 0))

    dirty = is_strategy_dirty()

    c1, c2 = st.columns([1, 2])
    with c1:
        if st.button("현재 전략으로 고정", use_container_width=True, type="primary"):
            apply_current_strategy()
            st.rerun()
    with c2:
        if dirty:
            st.warning("현재 선택 중인 전략이 아직 적용되지 않았습니다. 버튼을 눌러야 추천 결과와 백테스트에 반영됩니다.")
        else:
            st.success("현재 선택 중인 전략이 이미 앱에 적용되어 있습니다.")

    st.markdown("#### 현재 앱에 적용된 전략")
    st.write(f"**{st.session_state['applied_preset']}**")
    a1, a2, a3, a4 = st.columns(4)
    a1.metric("Momentum", metric_text(applied_weights[0], "percent", 0))
    a2.metric("Risk", metric_text(applied_weights[1], "percent", 0))
    a3.metric("Value", metric_text(applied_weights[2], "percent", 0))
    a4.metric("Quality", metric_text(applied_weights[3], "percent", 0))

    st.markdown("---")
    st.markdown("### 2) 지난달 보유 종목 확인")

    has_previous = st.radio(
        "저번 달에 구입해놓은 주식이 있나요?",
        ["없음", "있음"],
        horizontal=True,
        key="has_previous_holdings"
    )

    previous_holdings = []
    valid_previous_holdings = []

    if has_previous == "있음":
        st.text_area(
            "보유 중인 티커 입력 (쉼표로 구분, 예: AAPL, MSFT, NVDA)",
            key="previous_holdings_text",
            height=90
        )

        previous_holdings = parse_holdings(st.session_state["previous_holdings_text"])
        valid_previous_holdings = [x for x in previous_holdings if x in scored_df["Ticker"].tolist()]

        if previous_holdings and not valid_previous_holdings:
            st.warning("입력한 종목 중 현재 평가 가능한 종목이 없습니다. 일반 추천 결과를 보여줍니다.")

    st.markdown("---")
    st.markdown("### 3) 추천 결과")

    if has_previous == "있음" and valid_previous_holdings:
        portfolio_df = select_portfolio_with_buffer(
            scored_df,
            valid_previous_holdings,
            top_n=TOP_N,
            buffer_n=15
        )
        result_title = "이번 달 추천 포트폴리오"
    else:
        portfolio_df = scored_df.head(TOP_N).copy()
        result_title = "추천 종목 TOP 10"

    final_holdings = portfolio_df["Ticker"].tolist()
    kept_holdings = [x for x in final_holdings if x in valid_previous_holdings]
    new_holdings = [x for x in final_holdings if x not in valid_previous_holdings]
    removed_holdings = [x for x in valid_previous_holdings if x not in final_holdings]

    target_weight = 1 / TOP_N if TOP_N > 0 else 0

    r1, r2 = st.columns(2)
    r1.metric("추천 종목 수", f"{len(final_holdings)}개")
    r2.metric("종목당 목표 비중", metric_text(target_weight, "percent", 0))

    if has_previous == "있음" and valid_previous_holdings:
        c1, c2, c3 = st.columns(3)

        with c1:
            st.markdown("#### 계속 보유")
            for item in format_ticker_list(kept_holdings, fundamentals):
                st.write(f"- {item}")

        with c2:
            st.markdown("#### 신규 편입")
            for item in format_ticker_list(new_holdings, fundamentals):
                st.write(f"- {item}")

        with c3:
            st.markdown("#### 제외")
            for item in format_ticker_list(removed_holdings, fundamentals):
                st.write(f"- {item}")

    st.markdown(f"#### {result_title}")
    st.caption("아래 카드는 현재 적용된 전략 기준 추천 후보입니다.")

    render_stock_cards(portfolio_df, fundamentals, limit=10)

    st.markdown("### 더보기")
    with st.expander("추가 후보 20개 보기", expanded=False):
        render_stock_cards(scored_df.head(30).iloc[10:], fundamentals, limit=20)

        st.markdown("#### 표로 보기")
        extended_df = scored_df.head(30).copy()
        extended_table = enrich_table(extended_df, fundamentals)

        st.dataframe(
            extended_table[
                ["Company", "Momentum (12-1M)", "Risk (Vol)", "Value Score", "Quality Score", "Total Score"]
            ],
            use_container_width=True,
            hide_index=True
        )