from __future__ import annotations

from .base import ExpertOutput, clamp, required


def analyze(data: dict) -> dict:
    missing = required(data, ["account_balance", "risk_percent", "planned_sl_points", "point_value_per_lot"])
    if missing:
        return ExpertOutput(
            status="insufficient_data",
            reason=f"Campos ausentes: {', '.join(missing)}.",
        ).to_dict()

    balance = float(data["account_balance"])
    risk_percent = float(data["risk_percent"])
    sl_points = max(float(data["planned_sl_points"]), 1.0)
    point_value_per_lot = max(float(data["point_value_per_lot"]), 0.000001)
    max_daily_loss_percent = float(data.get("max_daily_loss_percent", 3.0))
    current_daily_loss_percent = float(data.get("current_daily_loss_percent", 0.0))
    requested_lot = data.get("requested_lot")

    risk_money = balance * risk_percent / 100.0
    suggested_lot = risk_money / (sl_points * point_value_per_lot)
    remaining_daily_risk = max_daily_loss_percent - current_daily_loss_percent

    trade_allowed = risk_percent > 0 and remaining_daily_risk > 0 and suggested_lot > 0
    if requested_lot is not None:
        requested_risk_money = float(requested_lot) * sl_points * point_value_per_lot
        requested_risk_percent = requested_risk_money / balance * 100.0 if balance > 0 else 999.0
        trade_allowed = trade_allowed and requested_risk_percent <= min(risk_percent, remaining_daily_risk)
    else:
        requested_risk_percent = None

    score = 0.8 if trade_allowed else -0.9

    return ExpertOutput(
        bias="neutral" if trade_allowed else "avoid",
        score=score,
        confidence=0.99,
        reason="Risco dentro dos limites." if trade_allowed else "Risco bloqueia a operacao.",
        features={
            "account_balance": balance,
            "risk_percent": risk_percent,
            "risk_money": round(risk_money, 2),
            "planned_sl_points": sl_points,
            "max_daily_loss_percent": max_daily_loss_percent,
            "current_daily_loss_percent": current_daily_loss_percent,
            "remaining_daily_risk_percent": round(remaining_daily_risk, 4),
            "requested_risk_percent": None if requested_risk_percent is None else round(requested_risk_percent, 4),
            "trade_allowed": trade_allowed,
            "suggested_lot": round(max(suggested_lot, 0.0), 4),
        },
    ).to_dict()
