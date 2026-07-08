from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from .signals import SignalSide, TradingSignal


@dataclass
class RiskConfig:
    risk_per_trade: float = 0.01
    max_daily_risk: float = 0.05
    min_lot: float = 0.01
    max_lot: float = 1.0
    min_rr: float = 1.5
    default_winrate: float = 0.52


@dataclass
class RiskDecision:
    can_trade: bool
    reason: str
    lot: float = 0.0
    rr: float = 0.0
    expected_value: float = 0.0


class RiskManager:
    """Dependency-light version of OMNIS risk manager for backtest/staging."""

    def __init__(self, config: RiskConfig | None = None):
        self.config = config or RiskConfig()
        self.daily_loss = 0.0

    def evaluate(
        self,
        signal: TradingSignal,
        balance: float,
        stop_loss: float,
        take_profit: float | None,
        tick_value: float = 1.0,
        tick_size: float = 0.0001,
        winrate: float | None = None,
        risk_regime_ok: bool = True,
    ) -> RiskDecision:
        if signal.side == SignalSide.HOLD:
            return RiskDecision(False, "Sinal HOLD")
        if not risk_regime_ok:
            return RiskDecision(False, "Regime de risco desfavoravel")
        if self.daily_loss >= self.config.max_daily_risk * balance:
            return RiskDecision(False, "Risco diario excedido")

        price = signal.price
        risk_dist = abs(price - stop_loss)
        if risk_dist <= 0:
            return RiskDecision(False, "Stop loss invalido")

        reward_dist = abs(take_profit - price) if take_profit else risk_dist * self.config.min_rr
        rr = reward_dist / risk_dist
        if rr < self.config.min_rr:
            return RiskDecision(False, f"RR baixo: {rr:.2f}", rr=rr)

        wr = winrate if winrate is not None else self.config.default_winrate
        ev = (wr * reward_dist) - ((1 - wr) * risk_dist)
        if ev <= 0:
            return RiskDecision(False, f"EV negativo: {ev:.6f}", rr=rr, expected_value=ev)

        lot = self.calculate_lot(balance, price, stop_loss, tick_value=tick_value, tick_size=tick_size)
        if lot <= 0:
            return RiskDecision(False, "Lote calculado como zero", rr=rr, expected_value=ev)

        return RiskDecision(True, "Risco aprovado", lot=lot, rr=rr, expected_value=ev)

    def calculate_lot(
        self,
        balance: float,
        entry: float,
        stop_loss: float,
        tick_value: float = 1.0,
        tick_size: float = 0.0001,
    ) -> float:
        stop_distance = abs(entry - stop_loss)
        if stop_distance <= 0 or tick_value <= 0 or tick_size <= 0:
            return 0.0
        risk_money = balance * self.config.risk_per_trade
        cost_per_lot = stop_distance / tick_size * tick_value
        lot = risk_money / cost_per_lot
        lot = max(self.config.min_lot, min(lot, self.config.max_lot))
        return round(lot, 2)

    def update_daily_loss(self, loss_value: float) -> None:
        self.daily_loss += abs(loss_value)


@dataclass
class TradeRiskGateConfig:
    max_risk_per_trade: float = 0.02
    max_daily_risk: float = 0.05
    min_rr: float = 1.5
    max_open_positions: int = 3
    max_positions_same_direction: int = 2
    max_leverage: float = 2.0


class TradeRiskGate:
    """Operational veto gate extracted from OMNIS_Copia RiskGuardian."""

    def __init__(self, config: TradeRiskGateConfig | None = None):
        self.config = config or TradeRiskGateConfig()
        self.daily_trades: list[dict[str, Any]] = []
        self.last_reset = datetime.now().date()

    def evaluate_trade(
        self,
        symbol: str,
        direction: int,
        entry_price: float,
        stop_loss: float,
        take_profit: float | None = None,
        current_positions: list[dict[str, Any]] | None = None,
        account_balance: float = 10000.0,
    ) -> dict[str, Any]:
        current_positions = current_positions or []
        self._check_daily_reset()
        if entry_price <= 0 or stop_loss <= 0:
            return self._veto("Precos invalidos")
        if direction not in {-1, 1}:
            return self._veto("Direcao invalida")

        risk_amount = abs(entry_price - stop_loss) / entry_price
        if risk_amount <= 0:
            return self._veto("Risco zerado")
        if take_profit is None:
            reward_amount = risk_amount * self.config.min_rr
            rr = self.config.min_rr
        else:
            reward_amount = abs(take_profit - entry_price) / entry_price
            rr = reward_amount / risk_amount

        position_size = min(self.config.max_risk_per_trade / (risk_amount + 1e-12), self.config.max_leverage)
        risk_value = position_size * risk_amount * account_balance
        base = {
            "approved": True,
            "reason": "Trade aprovado",
            "symbol": symbol,
            "position_size": position_size,
            "risk_amount": risk_amount,
            "reward_amount": reward_amount,
            "rr": rr,
            "risk_value": risk_value,
        }
        if rr < self.config.min_rr:
            return self._veto(f"RR muito baixo: {rr:.2f}", base)
        daily_risk_used = sum(float(item.get("risk_value", 0.0)) for item in self.daily_trades)
        if daily_risk_used + risk_value > self.config.max_daily_risk * account_balance:
            return self._veto("Risco diario excedido", base)
        if len(current_positions) >= self.config.max_open_positions:
            return self._veto("Maximo de posicoes abertas", base)
        same_direction = sum(1 for item in current_positions if int(item.get("direction", 0)) == direction)
        if same_direction >= self.config.max_positions_same_direction:
            return self._veto("Maximo de posicoes na mesma direcao", base)
        self.daily_trades.append({"symbol": symbol, "risk_value": risk_value, "timestamp": datetime.now()})
        return base

    def _veto(self, reason: str, base: dict[str, Any] | None = None) -> dict[str, Any]:
        result = {
            "approved": False,
            "reason": reason,
            "position_size": 0.0,
            "risk_amount": 0.0,
            "rr": 0.0,
            "risk_value": 0.0,
        }
        if base:
            result.update(base)
            result["approved"] = False
            result["reason"] = reason
        return result

    def _check_daily_reset(self) -> None:
        today = datetime.now().date()
        if today != self.last_reset:
            self.daily_trades = []
            self.last_reset = today
