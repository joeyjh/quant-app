import streamlit as st


PRESETS = {
    "기본 추천": {
        "momentum": 0.35,
        "risk": 0.25,
        "value": 0.20,
        "quality": 0.20,
        "description": "모멘텀을 중심으로 두되, 리스크·밸류·퀄리티를 함께 반영한 기본형입니다."
    },
    "추세형": {
        "momentum": 0.40,
        "risk": 0.20,
        "value": 0.20,
        "quality": 0.20,
        "description": "상승 추세를 조금 더 강하게 반영하는 preset입니다."
    },
    "안정형": {
        "momentum": 0.25,
        "risk": 0.35,
        "value": 0.20,
        "quality": 0.20,
        "description": "월 1회 운용에서 변동성 억제를 더 중시하는 preset입니다."
    },
    "직접 설정": {
        "momentum": 0.35,
        "risk": 0.25,
        "value": 0.20,
        "quality": 0.20,
        "description": "슬라이더로 4개 팩터 비중을 직접 조정합니다."
    }
}

PAGES = ["홈", "백테스트", "가격차트", "전략", "모의투자", "설정"]

PERIOD_OPTIONS = {
    "2년": 730,
    "1년": 365,
    "6개월": 180,
    "3개월": 90,
    "전체": None
}


def init_session_state():
    defaults = {
        "selected_page": "홈",

        # 사용자가 현재 화면에서 고르고 있는 draft 전략
        "selected_preset": "기본 추천",
        "last_preset": None,
        "momentum_weight": 0.35,
        "risk_weight": 0.25,
        "value_weight": 0.20,
        "quality_weight": 0.20,

        # 실제 앱 전체에 적용된 전략
        "applied_preset": "기본 추천",
        "applied_momentum_weight": 0.35,
        "applied_risk_weight": 0.25,
        "applied_value_weight": 0.20,
        "applied_quality_weight": 0.20,

        "has_previous_holdings": "없음",
        "previous_holdings_text": "",
        "price_chart_source": "추천 상위 종목",
        "selected_chart_ticker": None,
        "backtest_period_label": "2년",
        "price_period_label": "1년",
    }

    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def apply_preset_if_changed():
    current_preset = st.session_state["selected_preset"]
    last_preset = st.session_state["last_preset"]

    if current_preset != last_preset:
        preset = PRESETS[current_preset]
        st.session_state["momentum_weight"] = preset["momentum"]
        st.session_state["risk_weight"] = preset["risk"]
        st.session_state["value_weight"] = preset["value"]
        st.session_state["quality_weight"] = preset["quality"]
        st.session_state["last_preset"] = current_preset


def apply_current_strategy():
    st.session_state["applied_preset"] = st.session_state["selected_preset"]
    st.session_state["applied_momentum_weight"] = float(st.session_state["momentum_weight"])
    st.session_state["applied_risk_weight"] = float(st.session_state["risk_weight"])
    st.session_state["applied_value_weight"] = float(st.session_state["value_weight"])
    st.session_state["applied_quality_weight"] = float(st.session_state["quality_weight"])


def get_normalized_weights():
    momentum = float(st.session_state["applied_momentum_weight"])
    risk = float(st.session_state["applied_risk_weight"])
    value = float(st.session_state["applied_value_weight"])
    quality = float(st.session_state["applied_quality_weight"])

    total = momentum + risk + value + quality

    if total <= 0:
        return 0.35, 0.25, 0.20, 0.20

    return (
        momentum / total,
        risk / total,
        value / total,
        quality / total,
    )


def get_draft_normalized_weights():
    momentum = float(st.session_state["momentum_weight"])
    risk = float(st.session_state["risk_weight"])
    value = float(st.session_state["value_weight"])
    quality = float(st.session_state["quality_weight"])

    total = momentum + risk + value + quality

    if total <= 0:
        return 0.35, 0.25, 0.20, 0.20

    return (
        momentum / total,
        risk / total,
        value / total,
        quality / total,
    )


def is_strategy_dirty():
    draft = (
        st.session_state["selected_preset"],
        round(float(st.session_state["momentum_weight"]), 6),
        round(float(st.session_state["risk_weight"]), 6),
        round(float(st.session_state["value_weight"]), 6),
        round(float(st.session_state["quality_weight"]), 6),
    )

    applied = (
        st.session_state["applied_preset"],
        round(float(st.session_state["applied_momentum_weight"]), 6),
        round(float(st.session_state["applied_risk_weight"]), 6),
        round(float(st.session_state["applied_value_weight"]), 6),
        round(float(st.session_state["applied_quality_weight"]), 6),
    )

    return draft != applied