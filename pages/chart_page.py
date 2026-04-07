import streamlit as st

from chart_utils import make_price_chart
from state_utils import PERIOD_OPTIONS
from ui_utils import apply_period_filter, enrich_table


def render_price_chart_page(fundamentals, scored_df, get_chart):
    st.markdown("## 가격차트")
    st.caption("추천 상위 종목과 강한 모멘텀 종목을 빠르게 탐색합니다.")

    top_score_df = scored_df.head(20).copy()
    top_momentum_df = scored_df.sort_values("momentum", ascending=False).head(20).copy()

    mode = st.radio(
        "탐색 기준",
        ["추천 상위 종목", "급성장 후보"],
        horizontal=True,
        key="price_chart_source"
    )

    source_df = top_score_df if mode == "추천 상위 종목" else top_momentum_df
    source_table = enrich_table(source_df, fundamentals)

    st.dataframe(
        source_table[
            ["Company", "Momentum (12-1M)", "Risk (Vol)", "Value Score", "Quality Score", "Total Score"]
        ],
        use_container_width=True,
        hide_index=True
    )

    st.markdown("### 차트 기간 선택")
    st.radio(
        "가격차트 기간",
        list(PERIOD_OPTIONS.keys()),
        horizontal=True,
        key="price_period_label"
    )

    options = source_table["Company"].tolist()
    if options:
        selected_company = st.selectbox("종목 선택", options, index=0)
        selected_ticker = selected_company.split("(")[-1].replace(")", "").strip()
        chart_data = get_chart(selected_ticker)

        st.markdown(f"### {selected_ticker} 가격 차트")
        st.caption("x축: 날짜 / y축: 종가")

        if chart_data is not None and not chart_data.empty:
            chart_filtered = apply_period_filter(chart_data, st.session_state["price_period_label"], PERIOD_OPTIONS)
            st.plotly_chart(
                make_price_chart(chart_filtered, selected_ticker),
                use_container_width=True
            )
        else:
            st.warning("차트 데이터가 없습니다.")
    else:
        st.warning("표시할 종목이 없습니다.")