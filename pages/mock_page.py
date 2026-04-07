from datetime import datetime
import uuid

import streamlit as st

from config import TOP_N
from db import (
    delete_mock_portfolio,
    init_db,
    list_mock_portfolio_snapshots,
    load_mock_portfolio,
    save_mock_portfolio,
)
from ui_utils import enrich_table, format_ticker_list, metric_text


def render_mock_page(fundamentals, scored_df, weights):
    st.markdown("## 모의투자")
    st.caption("현재 추천 포트폴리오를 기록하고, 이전 기록과 비교할 수 있습니다.")

    init_db()

    current_top = scored_df.head(TOP_N).copy()
    current_tickers = current_top["Ticker"].tolist()
    weight_per_stock = 1 / TOP_N if TOP_N > 0 else 0
    preset_name = st.session_state.get("applied_preset", "기본 추천")

    st.markdown("### 현재 기록 가능한 포트폴리오")
    c1, c2, c3 = st.columns(3)
    c1.metric("현재 Preset", preset_name)
    c2.metric("종목 수", f"{len(current_tickers)}개")
    c3.metric("종목당 비중", metric_text(weight_per_stock, "percent", 0))

    current_table = enrich_table(current_top, fundamentals)
    st.dataframe(
        current_table[
            ["Company", "Momentum (12-1M)", "Risk (Vol)", "Value Score", "Quality Score", "Total Score"]
        ],
        use_container_width=True,
        hide_index=True
    )

    st.markdown("### 현재 추천 포트폴리오 저장")
    save_note = st.text_input(
        "기록 이름 (선택사항, 비워두면 날짜/시간으로 저장)",
        value=""
    )

    if st.button("현재 추천 포트폴리오 저장", type="primary", use_container_width=True):
        now = datetime.now()
        snapshot_date = now.strftime("%Y-%m-%d %H:%M")
        base_id = now.strftime("%Y%m%d_%H%M%S")
        note = save_note.strip()

        if note:
            snapshot_id = f"{base_id}_{note}"
        else:
            snapshot_id = f"{base_id}_{uuid.uuid4().hex[:6]}"

        save_mock_portfolio(
            snapshot_id=snapshot_id,
            snapshot_date=snapshot_date,
            preset_name=preset_name,
            weights=weights,
            tickers=current_tickers,
            weight_per_stock=weight_per_stock
        )
        st.success("모의투자 포트폴리오가 저장되었습니다.")
        st.rerun()

    snapshots = list_mock_portfolio_snapshots()

    st.markdown("### 저장된 모의투자 기록")

    if snapshots.empty:
        st.info("아직 저장된 모의투자 기록이 없습니다.")
        return

    display_options = []
    option_map = {}

    for _, row in snapshots.iterrows():
        label = (
            f"{row['snapshot_date']} | {row['preset_name']} | "
            f"{int(row['stock_count'])}종목 | {row['snapshot_id']}"
        )
        display_options.append(label)
        option_map[label] = row["snapshot_id"]

    selected_label = st.selectbox(
        "기록 선택",
        display_options,
        index=0
    )

    selected_snapshot_id = option_map[selected_label]
    selected_snapshot = load_mock_portfolio(selected_snapshot_id)

    if selected_snapshot.empty:
        st.warning("선택한 기록을 불러오지 못했습니다.")
        return

    st.markdown("### 선택한 기록 상세")
    top_info = selected_snapshot.iloc[0]

    i1, i2, i3 = st.columns(3)
    i1.metric("저장 날짜", str(top_info["snapshot_date"]))
    i2.metric("Preset", str(top_info["preset_name"]))
    i3.metric("종목 수", f"{len(selected_snapshot)}개")

    st.write(
        f"Momentum **{top_info['momentum_weight']:.0%}** · "
        f"Risk **{top_info['risk_weight']:.0%}** · "
        f"Value **{top_info['value_weight']:.0%}** · "
        f"Quality **{top_info['quality_weight']:.0%}**"
    )

    saved_tickers = selected_snapshot["ticker"].tolist()
    saved_names = format_ticker_list(saved_tickers, fundamentals)

    for item in saved_names:
        st.write(f"- {item}")

    st.markdown("### 현재 추천과 비교")

    kept = [x for x in current_tickers if x in saved_tickers]
    new_entries = [x for x in current_tickers if x not in saved_tickers]
    removed = [x for x in saved_tickers if x not in current_tickers]

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("#### 계속 보유")
        for item in format_ticker_list(kept, fundamentals):
            st.write(f"- {item}")

    with col2:
        st.markdown("#### 신규 편입")
        for item in format_ticker_list(new_entries, fundamentals):
            st.write(f"- {item}")

    with col3:
        st.markdown("#### 제외")
        for item in format_ticker_list(removed, fundamentals):
            st.write(f"- {item}")

    st.markdown("### 기록 삭제")
    if st.button("선택한 기록 삭제", use_container_width=True):
        delete_mock_portfolio(selected_snapshot_id)
        st.success("선택한 기록이 삭제되었습니다.")
        st.rerun()