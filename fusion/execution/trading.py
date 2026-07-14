"""
FUSION_V2 - Trading Executor
===========================
Inspirado em OMNIS: execuÃ§Ã£o MT5, ordens, gerenciamento
"""

try:
    import MetaTrader5 as mt5
except ImportError:
    mt5 = None
import pandas as pd
import time
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Tuple
from dataclasses import dataclass

from fusion.core.logger import get_logger
from fusion.core.config import get_config
from fusion.runtime_control import RuntimeControl


@dataclass
class TradeResult:
    success: bool
    ticket: int = 0
    message: str = ""
    price: float = 0.0


class OrderManager:
    """Gerenciador de ordens - inspirado em OMNIS."""
    
    def __init__(self):
        self.logger = get_logger("OrderManager")
        self.config = get_config()
    
    def get_position(self, symbol: str, magic: int = 0) -> Optional[dict]:
        """Busca posiÃ§Ã£o aberta para sÃ­mbolo."""
        positions = mt5.positions_get(symbol=symbol)
        if not positions:
            return None
        
        if magic > 0:
            positions = [p for p in positions if p.magic == magic]
        
        return positions[0] if positions else None
    
    def get_all_positions(self) -> List[dict]:
        """Retorna todas as posiÃ§Ãµes abertas."""
        positions = mt5.positions_get()
        return list(positions) if positions else []
    
    def get_symbol_info(self, symbol: str) -> Optional[dict]:
        """Retorna informaÃ§Ãµes do sÃ­mbolo."""
        info = mt5.symbol_info(symbol)
        return info if info else None
    
    def get_tick(self, symbol: str) -> Optional[dict]:
        """Retorna tick atual."""
        tick = mt5.symbol_info_tick(symbol)
        return tick if tick else None
    
    def calculate_lot(self, symbol: str, risk_pct: float = 1.0) -> float:
        """Lote fixo 0.01."""
        return 0.01
    
    def send_order(self, symbol: str, order_type: int, volume: float,
                   magic: int = 0, comment: str = "", sl: float = 0.0, tp: float = 0.0) -> TradeResult:
        """Envia ordem sem SL/TP no request inicial."""
        info = self.get_symbol_info(symbol)
        if not info:
            return TradeResult(False, 0, "SÃ­mbolo nÃ£o encontrado")
        if info.trade_mode == mt5.SYMBOL_TRADE_MODE_DISABLED:
            return TradeResult(False, 0, "Mercado fechado")
        tick = self.get_tick(symbol)
        if not tick:
            return TradeResult(False, 0, "Falha ao obter tick")
        if order_type == mt5.ORDER_TYPE_BUY:
            price = tick.ask
        else:
            price = tick.bid
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": float(f"{volume:.2f}"),
            "type": order_type,
            "price": float(price),
            "magic": magic,
            "comment": str(comment),
            "type_filling": mt5.ORDER_FILLING_IOC,
        }
        result = mt5.order_send(request)
        if result.retcode == mt5.TRADE_RETCODE_DONE:
            self.logger.info(f"Ordem executada: {symbol} {volume} @ {price:.5f}")
            return TradeResult(True, result.order, "ORDEM_EXECUTADA", float(price))
        else:
            msg = result.comment if result.comment else f"ERR_{result.retcode}"
            self.logger.error(f"Falha ordem: {symbol} | {msg}")
            return TradeResult(False, 0, f"MT5: {msg}")
    
    def close_position(self, ticket: int, volume: float = 0) -> TradeResult:
        """Fecha posiÃ§Ã£o."""
        positions = mt5.positions_get(ticket=ticket)
        if not positions:
            return TradeResult(False, 0, "PosiÃ§Ã£o nÃ£o encontrada")
        
        pos = positions[0]
        if volume == 0:
            volume = pos.volume
        
        order_type = mt5.ORDER_TYPE_SELL if pos.type == mt5.ORDER_TYPE_BUY else mt5.ORDER_TYPE_BUY
        
        tick = self.get_tick(pos.symbol)
        if not tick:
            return TradeResult(False, 0, "Falha tick")
        
        price = tick.bid if order_type == mt5.ORDER_TYPE_SELL else tick.ask
        
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": pos.symbol,
            "volume": float(volume),
            "type": order_type,
            "price": float(price),
            "position": ticket,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }
        
        result = mt5.order_send(request)
        
        if result.retcode == mt5.TRADE_RETCODE_DONE:
            self.logger.info(f"PosiÃ§Ã£o fechada: #{ticket} | {pos.symbol}")
            return TradeResult(True, ticket, "FECHADA", float(price))
        
        return TradeResult(False, ticket, f"MT5: {result.comment}")
    
    def modify_sl_tp(self, ticket: int, sl: float, tp: float) -> TradeResult:
        """Modifica SL/TP de posiÃ§Ã£o."""
        request = {
            "action": mt5.TRADE_ACTION_SLTP,
            "position": ticket,
            "sl": float(sl),
            "tp": float(tp),
        }
        
        result = mt5.order_send(request)
        
        if result.retcode == mt5.TRADE_RETCODE_DONE:
            return TradeResult(True, ticket, "MODIFICADO")
        
        return TradeResult(False, ticket, f"MT5: {result.comment}")


class TradingExecutor:
    """Executor de trading - inspirado em OMNIS."""
    
    MAGIC_BASE = {5: 202605, 15: 202615, 30: 202630}
    TF_CODES = {
        5: ("M5", "TIMEFRAME_M5"),
        15: ("M15", "TIMEFRAME_M15"),
        30: ("M30", "TIMEFRAME_M30"),
        60: ("H1", "TIMEFRAME_H1"),
        240: ("H4", "TIMEFRAME_H4"),
        1440: ("D1", "TIMEFRAME_D1"),
    }
    
    def __init__(self, simulation_mode: bool = False):
        self.logger = get_logger("TradingExecutor")
        self.config = get_config()
        self.runtime_control = RuntimeControl()
        self.order_manager = OrderManager()
        self.simulation_mode = simulation_mode
        self.positions_state: Dict[Tuple[str, int], dict] = {}
    
    def is_position_open(self, symbol: str, tf: int = 5, magic: int = None) -> bool:
        """Verifica se jÃ¡ hÃ¡ posiÃ§Ã£o aberta."""
        if tf == 0:
            positions = mt5.positions_get(symbol=symbol)
            return len(positions) > 0
        magic = magic if magic is not None else self.MAGIC_BASE.get(tf, 202605)
        return self.order_manager.get_position(symbol, magic) is not None
    
    def _position_count_by_type(self, symbol: str) -> Tuple[int, int]:
        """Retorna (qtd_compra, qtd_venda) para o sÃ­mbolo."""
        positions = mt5.positions_get(symbol=symbol)
        if not positions:
            return (0, 0)
        buy_count = sum(1 for p in positions if p.type == mt5.ORDER_TYPE_BUY)
        sell_count = sum(1 for p in positions if p.type == mt5.ORDER_TYPE_SELL)
        return (buy_count, sell_count)

    def _position_count_by_symbol_type(self, symbol: str, order_type: int = None) -> int:
        """Conta posicoes do simbolo, independente de magic."""
        positions = mt5.positions_get(symbol=symbol)
        if not positions:
            return 0
        return sum(1 for p in positions if order_type is None or p.type == order_type)
    
    def _position_count_by_magic_type(self, symbol: str, magic: int, order_type: int = None) -> int:
        """Conta posicoes por simbolo, magic e opcionalmente tipo."""
        positions = mt5.positions_get(symbol=symbol)
        if not positions:
            return 0
        return sum(
            1 for p in positions
            if p.magic == magic and (order_type is None or p.type == order_type)
        )

    def _position_count_by_magics_type(self, symbol: str, magics: List[int], order_type: int = None) -> int:
        """Conta posicoes por simbolo, lista de magics e opcionalmente tipo."""
        positions = mt5.positions_get(symbol=symbol)
        if not positions:
            return 0
        magic_set = set(magics)
        return sum(
            1 for p in positions
            if p.magic in magic_set and (order_type is None or p.type == order_type)
        )

    def _floating_loss_guard(self) -> Tuple[bool, str]:
        """Bloqueia novas ordens quando o prejuizo flutuante atingir o limite em dinheiro."""
        daily_ok, daily_reason = self._daily_loss_guard()
        if not daily_ok:
            return False, daily_reason

        cfg = self.config.get("trading.floating_loss_guard", {}) or {}
        if not bool(cfg.get("enabled", False)):
            return True, "OK"
        if mt5 is None:
            return False, "FLOATING_LOSS_GUARD_MT5_INDISPONIVEL"

        runtime_limit = self.runtime_control.get("trading.max_floating_loss_money")
        limit = float(runtime_limit if runtime_limit is not None else cfg.get("max_loss_money", 70.0) or 70.0)
        positions = mt5.positions_get()
        floating_profit = sum(float(getattr(pos, "profit", 0.0) or 0.0) for pos in positions) if positions else 0.0
        floating_loss = max(0.0, -floating_profit)
        if floating_loss >= limit:
            reason = f"FLOATING_LOSS_GUARD:{floating_loss:.2f}>={limit:.2f}"
            self.logger.warning(f"Novas ordens bloqueadas: prejuizo flutuante ${floating_loss:.2f} >= ${limit:.2f}")
            return False, reason
        return True, "OK"

    def _daily_loss_guard(self) -> Tuple[bool, str]:
        """Bloqueia novas ordens quando a perda realizada do dia atingir o limite."""
        cfg = self.config.get("trading.daily_loss_guard", {}) or {}
        if not bool(cfg.get("enabled", False)):
            return True, "OK"
        if mt5 is None:
            return False, "DAILY_LOSS_GUARD_MT5_INDISPONIVEL"

        now = datetime.now()
        day_start = datetime(now.year, now.month, now.day)
        try:
            deals = mt5.history_deals_get(day_start, now)
        except Exception as exc:
            self.logger.warning(f"Falha ao consultar historico do dia para risco diario: {exc}")
            return True, "OK"
        if not deals:
            return True, "OK"

        include_costs = bool(cfg.get("include_commission_swap", True))
        realized = 0.0
        for deal in deals:
            profit = float(getattr(deal, "profit", 0.0) or 0.0)
            if include_costs:
                profit += float(getattr(deal, "commission", 0.0) or 0.0)
                profit += float(getattr(deal, "swap", 0.0) or 0.0)
            realized += profit

        realized_loss = max(0.0, -realized)
        account = mt5.account_info()
        balance = float(getattr(account, "balance", 0.0) or 0.0) if account else 0.0
        runtime_money = self.runtime_control.get("trading.max_daily_loss_money")
        max_loss_money = float(runtime_money if runtime_money is not None else cfg.get("max_loss_money", 0.0) or 0.0)
        max_loss_pct = float(cfg.get("max_loss_pct", 0.0) or 0.0)
        pct_limit_money = (balance * max_loss_pct / 100.0) if balance > 0 and max_loss_pct > 0 else 0.0
        limits = [value for value in [max_loss_money, pct_limit_money] if value > 0]
        if not limits:
            return True, "OK"

        limit = min(limits)
        if realized_loss >= limit:
            reason = f"DAILY_LOSS_GUARD:{realized_loss:.2f}>={limit:.2f}"
            self.logger.warning(
                f"Novas ordens bloqueadas: perda realizada do dia ${realized_loss:.2f} >= ${limit:.2f}"
            )
            return False, reason
        return True, "OK"

    def price_levels_from_points(self, symbol: str, order_type: int,
                                 points_tp: int = 0, points_sl: int = 0) -> Tuple[float, float]:
        info = self.order_manager.get_symbol_info(symbol)
        tick = self.order_manager.get_tick(symbol)
        if not info or not tick:
            return 0.0, 0.0
        point = float(info.point)
        entry = float(tick.ask if order_type == mt5.ORDER_TYPE_BUY else tick.bid)
        if order_type == mt5.ORDER_TYPE_BUY:
            sl = entry - (points_sl * point) if points_sl else 0.0
            tp = entry + (points_tp * point) if points_tp else 0.0
        else:
            sl = entry + (points_sl * point) if points_sl else 0.0
            tp = entry - (points_tp * point) if points_tp else 0.0
        return sl, tp

    def _runtime_symbol_cfg(self, symbol: str) -> dict:
        symbols = self.runtime_control.section("risk_by_symbol")
        if not isinstance(symbols, dict):
            return {}
        return symbols.get(str(symbol or "").upper(), {}) or {}

    def _runtime_max_positions(self, symbol: str, fallback: int) -> int:
        symbol_cfg = self._runtime_symbol_cfg(symbol)
        value = symbol_cfg.get("max_positions", self.runtime_control.get("trading.max_positions_per_symbol"))
        if value is None:
            return int(fallback)
        try:
            return max(int(value), 0)
        except (TypeError, ValueError):
            return int(fallback)

    def _runtime_tp_sl(self, symbol: str, tp_points: int, sl_points: int) -> tuple[int, int]:
        symbol_key = str(symbol or "").upper()
        symbol_cfg = self.runtime_control.section("symbol_tp_sl").get(symbol_key, {}) or {}
        global_cfg = self.runtime_control.section("global_tp_sl")
        if bool(global_cfg.get("use_runtime_override", False)):
            tp_points = int(global_cfg.get("tp_points", tp_points) or tp_points or 0)
            sl_points = int(global_cfg.get("sl_points", sl_points) or sl_points or 0)
        if symbol_cfg:
            tp_points = int(symbol_cfg.get("tp_points", tp_points) or tp_points or 0)
            sl_points = int(symbol_cfg.get("sl_points", sl_points) or sl_points or 0)
        return int(tp_points or 0), int(sl_points or 0)

    def _fresh_rates_guard(self, symbol: str, tf: int) -> Tuple[bool, str]:
        # Ultima trava antes do order_send: nao opera com candle fechado desatualizado.
        if mt5 is None:
            return False, "FRESH_RATES_GUARD_MT5_INDISPONIVEL"
        tf_name, tf_attr = self.TF_CODES.get(int(tf), ("M5", "TIMEFRAME_M5"))
        tf_code = getattr(mt5, tf_attr, None)
        if tf_code is None:
            return False, f"FRESH_RATES_GUARD_TIMEFRAME_INVALIDO:{tf}"
        rates = mt5.copy_rates_from_pos(symbol, tf_code, 1, 2)
        if rates is None or len(rates) == 0:
            return False, f"FRESH_RATES_GUARD_SEM_CANDLE:{symbol}:{tf_name}"
        last_time = int(rates[-1]["time"])
        last_dt = datetime.utcfromtimestamp(last_time)
        age_minutes = (datetime.utcnow() - last_dt).total_seconds() / 60.0
        tf_minutes = int(tf or 5)
        max_age_minutes = max(float(tf_minutes) * 3.0, 30.0)
        if tf_minutes >= 1440:
            max_age_minutes = float(tf_minutes) * 3.0
        if age_minutes > max_age_minutes:
            reason = f"FRESH_RATES_GUARD_CANDLE_ANTIGO:{symbol}:{tf_name}:{age_minutes:.0f}m>{max_age_minutes:.0f}m"
            self.logger.warning(reason)
            return False, reason
        return True, "OK"

    def execute_buy(self, symbol: str, tf: int, mode: str = "NORMAL") -> TradeResult:
        """Executa compra â€” mÃ¡ximo 1 compra por ativo."""
        ok, reason = self._floating_loss_guard()
        if not ok:
            return TradeResult(False, 0, reason)
        buy_count, _ = self._position_count_by_type(symbol)
        if buy_count >= 1:
            return TradeResult(False, 0, "COMPRA_JA_EXISTE")
        volume = self.order_manager.calculate_lot(symbol, self.config.risk.max_risk_per_trade)
        magic = self.MAGIC_BASE.get(tf, 202605)
        ok, reason = self._fresh_rates_guard(symbol, tf)
        if ok:
            ok, reason = self._ema_order_guard(symbol, tf, mt5.ORDER_TYPE_BUY)
        if ok:
            ok, reason = self._extreme_order_guard(symbol, tf, mt5.ORDER_TYPE_BUY)
        if not ok:
            return TradeResult(False, 0, reason)
        return self.order_manager.send_order(symbol, mt5.ORDER_TYPE_BUY, volume, magic, mode)
    
    def execute_sell(self, symbol: str, tf: int, mode: str = "NORMAL") -> TradeResult:
        """Executa venda â€” mÃ¡ximo 1 venda por ativo."""
        ok, reason = self._floating_loss_guard()
        if not ok:
            return TradeResult(False, 0, reason)
        _, sell_count = self._position_count_by_type(symbol)
        if sell_count >= 1:
            return TradeResult(False, 0, "VENDA_JA_EXISTE")
        volume = self.order_manager.calculate_lot(symbol, self.config.risk.max_risk_per_trade)
        magic = self.MAGIC_BASE.get(tf, 202605)
        ok, reason = self._fresh_rates_guard(symbol, tf)
        if ok:
            ok, reason = self._ema_order_guard(symbol, tf, mt5.ORDER_TYPE_SELL)
        if ok:
            ok, reason = self._extreme_order_guard(symbol, tf, mt5.ORDER_TYPE_SELL)
        if not ok:
            return TradeResult(False, 0, reason)
        return self.order_manager.send_order(symbol, mt5.ORDER_TYPE_SELL, volume, magic, mode)

    def execute_buy_strategy(self, symbol: str, tf: int, mode: str, magic: int,
                             max_positions: int = 1, tp_points: int = 0, sl_points: int = 0,
                             magic_group: List[int] = None, count_any_direction: bool = False,
                             count_system_symbol: bool = False, p_buy: float = 0.0,
                             p_sell: float = 0.0) -> TradeResult:
        """Executa compra isolada por magic/estrategia."""
        ok, reason = self._floating_loss_guard()
        if not ok:
            return TradeResult(False, 0, reason)
        max_positions = self._runtime_max_positions(symbol, max_positions)
        order_type = None if count_any_direction else mt5.ORDER_TYPE_BUY
        if count_system_symbol:
            buy_count = self._position_count_by_symbol_type(symbol, order_type)
        elif magic_group:
            buy_count = self._position_count_by_magics_type(symbol, magic_group, order_type)
        else:
            buy_count = self._position_count_by_magic_type(symbol, magic, order_type)
        if buy_count >= max_positions:
            return TradeResult(False, 0, "POSICAO_JA_EXISTE")
        tp_points, sl_points = self._runtime_tp_sl(symbol, tp_points, sl_points)
        volume = self.order_manager.calculate_lot(symbol, self.config.risk.max_risk_per_trade)
        sl, tp = self.price_levels_from_points(symbol, mt5.ORDER_TYPE_BUY, tp_points, sl_points)
        ok, reason = self._fresh_rates_guard(symbol, tf)
        if ok:
            ok, reason = self._ema_order_guard(symbol, tf, mt5.ORDER_TYPE_BUY)
        if ok:
            ok, reason = self._extreme_order_guard(symbol, tf, mt5.ORDER_TYPE_BUY, p_buy=p_buy, p_sell=p_sell)
        if not ok:
            return TradeResult(False, 0, reason)
        return self.order_manager.send_order(symbol, mt5.ORDER_TYPE_BUY, volume, magic, mode, sl=sl, tp=tp)

    def execute_sell_strategy(self, symbol: str, tf: int, mode: str, magic: int,
                              max_positions: int = 1, tp_points: int = 0, sl_points: int = 0,
                              magic_group: List[int] = None, count_any_direction: bool = False,
                              count_system_symbol: bool = False, p_buy: float = 0.0,
                              p_sell: float = 0.0) -> TradeResult:
        """Executa venda isolada por magic/estrategia."""
        ok, reason = self._floating_loss_guard()
        if not ok:
            return TradeResult(False, 0, reason)
        max_positions = self._runtime_max_positions(symbol, max_positions)
        order_type = None if count_any_direction else mt5.ORDER_TYPE_SELL
        if count_system_symbol:
            sell_count = self._position_count_by_symbol_type(symbol, order_type)
        elif magic_group:
            sell_count = self._position_count_by_magics_type(symbol, magic_group, order_type)
        else:
            sell_count = self._position_count_by_magic_type(symbol, magic, order_type)
        if sell_count >= max_positions:
            return TradeResult(False, 0, "POSICAO_JA_EXISTE")
        tp_points, sl_points = self._runtime_tp_sl(symbol, tp_points, sl_points)
        volume = self.order_manager.calculate_lot(symbol, self.config.risk.max_risk_per_trade)
        sl, tp = self.price_levels_from_points(symbol, mt5.ORDER_TYPE_SELL, tp_points, sl_points)
        ok, reason = self._fresh_rates_guard(symbol, tf)
        if ok:
            ok, reason = self._ema_order_guard(symbol, tf, mt5.ORDER_TYPE_SELL)
        if ok:
            ok, reason = self._extreme_order_guard(symbol, tf, mt5.ORDER_TYPE_SELL, p_buy=p_buy, p_sell=p_sell)
        if not ok:
            return TradeResult(False, 0, reason)
        return self.order_manager.send_order(symbol, mt5.ORDER_TYPE_SELL, volume, magic, mode, sl=sl, tp=tp)

    def _ema_order_guard(self, symbol: str, tf: int, order_type: int) -> Tuple[bool, str]:
        """Ultima trava antes do order_send: alinhamento e distancia minima das EMAs."""
        cfg = self.config.get("entry_filters.ema_alignment", {}) or {}
        runtime_filters = self.runtime_control.section("filters")
        runtime_enabled = runtime_filters.get("ema_alignment_enabled")
        runtime_mode = str(runtime_filters.get("ema_alignment_mode", cfg.get("mode", "block")) or "block").lower()
        if runtime_enabled is False or runtime_mode == "shadow":
            return True, "OK"
        if not bool(cfg.get("enabled", True)):
            return True, "OK"
        if mt5 is None:
            return False, "EMA_GUARD_MT5_INDISPONIVEL"
        tf_name, tf_attr = self.TF_CODES.get(int(tf), ("M5", "TIMEFRAME_M5"))
        tf_code = getattr(mt5, tf_attr, None)
        if tf_code is None:
            return False, f"EMA_GUARD_TIMEFRAME_INVALIDO:{tf}"

        periods = list(cfg.get("periods", [9, 21, 50]) or [9, 21, 50])
        if len(periods) != 3:
            periods = [9, 21, 50]
        fast, mid, slow = [int(period) for period in periods]
        bars = max(slow + 10, int(cfg.get("bars", 80) or 80))
        start_pos = 1 if bool(cfg.get("use_closed_candle", True)) else 0
        rates = mt5.copy_rates_from_pos(symbol, tf_code, start_pos, bars)
        if rates is None or len(rates) < slow + 5:
            return False, f"EMA_GUARD_DADOS_INSUFICIENTES:{symbol}:{tf_name}"

        df = pd.DataFrame(rates).sort_values("time").reset_index(drop=True)
        close = df["close"].astype(float)
        ema_fast = float(close.ewm(span=fast, adjust=False).mean().iloc[-1])
        ema_mid = float(close.ewm(span=mid, adjust=False).mean().iloc[-1])
        ema_slow = float(close.ewm(span=slow, adjust=False).mean().iloc[-1])

        info = self.order_manager.get_symbol_info(symbol)
        point = float(getattr(info, "point", 0.0) or 0.0) if info else 0.0
        if point <= 0:
            tick_size = float(getattr(info, "trade_tick_size", 0.0) or 0.0) if info else 0.0
            point = tick_size
        if point <= 0:
            return False, f"EMA_GUARD_POINT_INDISPONIVEL:{symbol}"

        distance_cfg = cfg.get("min_distance_points", {}) or {}
        default_dist = distance_cfg.get("default", {}) or {}
        timeframe_dist = (distance_cfg.get("by_timeframe", {}) or {}).get(tf_name, {}) or {}
        min_fast_mid = float(timeframe_dist.get(f"ema{fast}_ema{mid}", timeframe_dist.get("ema9_ema21", default_dist.get("ema9_ema21", 0))) or 0)
        min_mid_slow = float(timeframe_dist.get(f"ema{mid}_ema{slow}", timeframe_dist.get("ema21_ema50", default_dist.get("ema21_ema50", 0))) or 0)

        if order_type == mt5.ORDER_TYPE_BUY:
            aligned = ema_fast > ema_mid > ema_slow
            fast_mid_points = (ema_fast - ema_mid) / point
            mid_slow_points = (ema_mid - ema_slow) / point
            side = "BUY"
        else:
            aligned = ema_fast < ema_mid < ema_slow
            fast_mid_points = (ema_mid - ema_fast) / point
            mid_slow_points = (ema_slow - ema_mid) / point
            side = "SELL"

        if not aligned:
            self.logger.warning(
                f"EMA_GUARD bloqueou {side} {symbol} {tf_name}: "
                f"EMA{fast}={ema_fast:.5f} EMA{mid}={ema_mid:.5f} EMA{slow}={ema_slow:.5f}"
            )
            return False, "EMA_GUARD_NAO_ALINHADA"
        if fast_mid_points < min_fast_mid or mid_slow_points < min_mid_slow:
            self.logger.warning(
                f"EMA_GUARD bloqueou {side} {symbol} {tf_name}: distancia insuficiente "
                f"EMA{fast}-EMA{mid}={fast_mid_points:.1f}p min={min_fast_mid:.1f}p | "
                f"EMA{mid}-EMA{slow}={mid_slow_points:.1f}p min={min_mid_slow:.1f}p"
            )
            return False, "EMA_GUARD_DISTANCIA_INSUFICIENTE"
        return True, "OK"

    def _extreme_order_guard(
        self,
        symbol: str,
        tf: int,
        order_type: int,
        p_buy: float = 0.0,
        p_sell: float = 0.0,
    ) -> Tuple[bool, str]:
        """Bloqueia compra em topo/venda em fundo salvo rompimento validado."""
        cfg = self.config.get("entry_filters.entry_timing", {}) or {}
        runtime_extreme = self.runtime_control.get("filters.block_top_bottom_without_breakout")
        if runtime_extreme is not None and not bool(runtime_extreme):
            return True, "OK"
        if not bool(cfg.get("block_extreme_entries", True)):
            return True, "OK"
        if mt5 is None:
            return False, "EXTREME_GUARD_MT5_INDISPONIVEL"
        tf_name, tf_attr = self.TF_CODES.get(int(tf), ("M5", "TIMEFRAME_M5"))
        tf_code = getattr(mt5, tf_attr, None)
        if tf_code is None:
            return False, f"EXTREME_GUARD_TIMEFRAME_INVALIDO:{tf}"

        bars = max(80, int(cfg.get("bars", 260) or 260))
        rates = mt5.copy_rates_from_pos(symbol, tf_code, 1, bars)
        if rates is None or len(rates) < 60:
            return False, f"EXTREME_GUARD_DADOS_INSUFICIENTES:{symbol}:{tf_name}"

        df = pd.DataFrame(rates).sort_values("time").reset_index(drop=True)
        close = df["close"].astype(float)
        high = df["high"].astype(float)
        low = df["low"].astype(float)
        tr = pd.concat(
            [
                high - low,
                (high - close.shift(1)).abs(),
                (low - close.shift(1)).abs(),
            ],
            axis=1,
        ).max(axis=1)
        atr = float(tr.rolling(14).mean().iloc[-1] or 0.0)
        if atr <= 0:
            return False, f"EXTREME_GUARD_ATR_INDISPONIVEL:{symbol}:{tf_name}"

        last_close = float(close.iloc[-1])
        prior_high = float(high.shift(1).rolling(20).max().iloc[-1])
        prior_low = float(low.shift(1).rolling(20).min().iloc[-1])
        ema21 = float(close.ewm(span=21, adjust=False).mean().iloc[-1])
        volume = df["tick_volume"].astype(float) if "tick_volume" in df.columns else pd.Series(dtype=float)
        volume_ratio = 0.0
        if len(volume) >= 21:
            avg_volume = float(volume.shift(1).rolling(20).mean().iloc[-1] or 0.0)
            if avg_volume > 0:
                volume_ratio = float(volume.iloc[-1] / avg_volume)
        top_distance_atr = (prior_high - last_close) / atr
        bottom_distance_atr = (last_close - prior_low) / atr
        extension_atr = (last_close - ema21) / atr
        extreme_distance = float(cfg.get("top_bottom_distance_atr", 0.35) or 0.35)
        extension_limit = float(cfg.get("extension_atr", 1.20) or 1.20)
        require_breakout_volume = bool(cfg.get("require_breakout_volume", False))
        min_breakout_volume_ratio = float(cfg.get("min_breakout_volume_ratio", 1.10) or 1.10)

        if order_type == mt5.ORDER_TYPE_BUY:
            at_extreme = top_distance_atr <= extreme_distance or extension_atr >= extension_limit
            valid_breakout = last_close > prior_high and (
                not require_breakout_volume or volume_ratio >= min_breakout_volume_ratio
            )
            reason = "EXTREME_GUARD_COMPRA_TOPO_SEM_ROMPIMENTO"
            side = "BUY"
        else:
            at_extreme = bottom_distance_atr <= extreme_distance or extension_atr <= -extension_limit
            valid_breakout = last_close < prior_low and (
                not require_breakout_volume or volume_ratio >= min_breakout_volume_ratio
            )
            reason = "EXTREME_GUARD_VENDA_FUNDO_SEM_ROMPIMENTO"
            side = "SELL"
        if not at_extreme:
            return True, "OK"
        if valid_breakout:
            self.logger.info(
                f"EXTREME_GUARD permitiu {side} {symbol} {tf_name} por rompimento validado: "
                f"close={last_close:.5f} high20={prior_high:.5f} low20={prior_low:.5f} vol_ratio={volume_ratio:.2f}"
            )
            return True, "OK"
        self.logger.warning(
            f"EXTREME_GUARD bloqueou {side} {symbol} {tf_name}: "
            f"top_dist={top_distance_atr:.2f}atr bottom_dist={bottom_distance_atr:.2f}atr "
            f"extension={extension_atr:.2f}atr close={last_close:.5f} "
            f"high20={prior_high:.5f} low20={prior_low:.5f} vol_ratio={volume_ratio:.2f}"
        )
        return False, reason
    
    def close_all_for_symbol(self, symbol: str) -> List[TradeResult]:
        """Fecha todas as posiÃ§Ãµes de um sÃ­mbolo."""
        positions = self.order_manager.get_all_positions()
        symbol_positions = [p for p in positions if p.symbol == symbol]
        
        results = []
        for pos in symbol_positions:
            result = self.order_manager.close_position(pos.ticket)
            results.append(result)
        
        return results

