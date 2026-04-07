import streamlit as st


def render_settings_page():
    st.markdown("## 설정")
    st.caption("앱 운영과 사용 환경 관련 설정을 모아두는 공간입니다.")
    st.write("- DB 업데이트 주기: 매달 말 또는 월초 1회")
    st.write("- 현재 구조: Streamlit + SQLite + S&P500 universe")
    st.write("- 향후 확장: 전략 저장 / 모의투자 / 진짜 앱 전환")