import pandas as pd


def calculate_cagr(bt):
    if bt is None or len(bt) == 0:
        return None

    years = len(bt) / 12
    if years <= 0:
        return None

    total_return = bt.iloc[-1]
    try:
        return (1 + total_return) ** (1 / years) - 1
    except Exception:
        return None


def calculate_sharpe(bt):
    if bt is None or len(bt) < 2:
        return None

    returns = bt.diff().dropna()
    if returns.std() == 0:
        return None

    return returns.mean() / returns.std() * (12 ** 0.5)


def calculate_mdd(bt):
    if bt is None or len(bt) < 2:
        return None

    returns = bt.diff().dropna()
    if len(returns) == 0:
        return None

    cum = (1 + returns).cumprod()
    peak = cum.cummax()
    drawdown = (cum - peak) / peak
    return drawdown.min()