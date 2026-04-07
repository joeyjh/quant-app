import streamlit as st

from state_utils import PRESETS


def render_strategy_page():
    st.markdown("## 전략")
    st.caption("현재 사용 가능한 전략과 비중 철학을 확인합니다.")

    for name, preset in PRESETS.items():
        st.markdown(f"### {name}")
        st.write(preset["description"])
        st.write(
            f"- Momentum: {preset['momentum']:.0%}  \n"
            f"- Risk: {preset['risk']:.0%}  \n"
            f"- Value: {preset['value']:.0%}  \n"
            f"- Quality: {preset['quality']:.0%}"
        )

    st.info("다음 단계에서는 사용자가 만든 전략을 저장하고 불러오는 기능을 여기에 추가하면 됩니다.")