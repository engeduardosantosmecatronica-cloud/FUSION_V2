from __future__ import annotations

import pandas as pd


def build_signal_figure(
    df: pd.DataFrame,
    date_col: str = "date",
    signal_col: str = "signal",
    title: str = "Regime + Sinais + TP/SL",
):
    """Plotly candlestick helper extracted from ALPHAEDU plot_trading_signals.py."""
    import plotly.graph_objects as go

    data = df.copy()
    if date_col not in data.columns:
        data[date_col] = data.index
    fig = go.Figure()
    fig.add_trace(
        go.Candlestick(
            x=data[date_col],
            open=data["open"],
            high=data["high"],
            low=data["low"],
            close=data["close"],
            name="Candles",
        )
    )
    if signal_col in data.columns:
        buy = data[data[signal_col] > 0]
        sell = data[data[signal_col] < 0]
        fig.add_trace(
            go.Scatter(
                x=buy[date_col],
                y=buy["close"],
                mode="markers",
                marker=dict(symbol="triangle-up", size=8),
                name="BUY",
            )
        )
        fig.add_trace(
            go.Scatter(
                x=sell[date_col],
                y=sell["close"],
                mode="markers",
                marker=dict(symbol="triangle-down", size=8),
                name="SELL",
            )
        )
    for col in ("take_profit", "tp_level", "stop_loss", "sl_level"):
        if col in data.columns:
            fig.add_trace(go.Scatter(x=data[date_col], y=data[col], mode="lines", name=col))
    fig.update_layout(title=title, xaxis_title="Tempo", yaxis_title="Preco", xaxis_rangeslider_visible=False)
    return fig
