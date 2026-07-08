/**
 * Mock do FusionRuntimeControl — substituir por chamada real ao Fusion
 * Representa o fusion_runtime_control.json + campos migráveis do fusion_config.yaml
 */

export function mockFusionRuntimeControl() {
  return {
    enabled: true,
    loop: { min_cycle_seconds: 5 },
    symbols: ['EURUSD', 'GBPUSD', 'USDJPY', 'XAUUSD', 'AUDCAD', 'GBPJPY', 'USDCAD'],
    broker: {
      terminal_path: 'C:/Program Files/MetaTrader 5/terminal64.exe',
      login: 123456,
      password: '••••••••',
      server: 'MetaQuotes-Demo',
      startup_timeout: 30,
    },
    data: {
      timeframe_default: 'H1',
      data_dir: './data',
      parquet_dir: './data/parquet',
      symbol_mapping: { XAUUSD: 'GOLD', BTCUSD: 'BTCUSD' },
      point_values: { EURUSD: 10, GBPUSD: 10, USDJPY: 0.077, XAUUSD: 1 },
    },
    trading: {
      allow_new_orders: true,
      execution_mode: 'automatic',
      manual_approval: {
        enabled: false,
        request_file: './fusion_manual_request.json',
        response_file: './fusion_manual_response.json',
        timeout_seconds: 60,
      },
      close_on_opposite_signal: {
        enabled: true,
        source: 'fusion',
        min_loss_money: 0,
        scope: 'system',
        reason_code: 'OPPOSITE_SIGNAL',
      },
      floating_loss_guard: {
        enabled: true,
        max_loss_money: 200,
        scope: 'system',
      },
      daily_loss_guard: {
        enabled: true,
        max_loss_pct: 2.0,
        max_loss_money: 300,
        include_commission_swap: true,
      },
      reentry_cooldown_after_close: {
        enabled: true,
        seconds: 120,
        scope: 'symbol',
      },
      position_limits: {
        enabled: true,
        scope: 'system',
        max_per_symbol: 2,
        mode: 'any_direction',
      },
    },
    risk: {
      max_risk_per_trade: 1.0,
      max_daily_loss: 3.0,
      max_positions: 5,
      lot_step: 0.01,
      min_lot: 0.01,
      max_lot: 1.0,
      default_sl_points: 30,
    },
    signal: {
      buy_threshold: 0.55,
      sell_threshold: 0.55,
      confidence_filter: 0.60,
      min_signal_strength: 0.50,
      invert_signals: false,
      inverted_signal_groups: [],
    },
    signal_overrides: {
      enabled: false,
      rules: [
        { symbol: 'EURUSD', timeframe: 'M5', action: 'block_buy', enabled: false, reason: 'Tendência de baixa macro', valid_until: '2026-12-31T23:59:00' },
        { symbol: 'GBPJPY', timeframe: 'H1', action: 'reduce_confidence', enabled: true, reason: 'Alta volatilidade', valid_until: '2026-12-31T23:59:00' },
      ],
    },
    entry_filters: {
      market_alignment: {
        enabled: true, mode: 'block', reason_code: 'MARKET_ALIGNMENT',
        log_each_check: false, write_monitor_log: false,
        block_states: ['bear', 'choppy'],
        min_alignment_score: 0.4, min_structural_score: 0.3, chop_abs_score: 0.2,
        require_h1_or_h4_alignment: true, block_lower_tf_against_h4_d1: true,
        timeframe_weights: { M5: 0.5, M15: 0.7, M30: 0.8, H1: 1.0, H4: 1.2, D1: 1.5 },
      },
      timeframe_consensus: {
        enabled: true, mode: 'block', reason_code: 'TF_CONSENSUS',
        log_each_check: false, block_states: ['conflict'],
        wait_edge: 0.1, min_valid_timeframes: 2, min_consensus_score: 0.5,
        min_structural_score: 0.3, require_h1_or_h4_alignment: true,
        block_lower_tf_against_h4_d1: false,
        timeframe_weights: { M5: 0.5, M15: 0.7, M30: 0.8, H1: 1.0, H4: 1.2, D1: 1.5 },
      },
      session_context: {
        enabled: true, mode: 'block',
        low_liquidity_start_hour_utc: 22, low_liquidity_end_hour_utc: 2,
        asian_start_hour_utc: 0, asian_end_hour_utc: 8,
        london_start_hour_utc: 8, london_end_hour_utc: 16,
        new_york_start_hour_utc: 13, new_york_end_hour_utc: 21,
        london_open_risk_minutes: 15, new_york_open_risk_minutes: 15,
        transition_risk_minutes: 10, friday_cutoff_hour_utc: 20,
        scalping_timeframes: ['M1', 'M5'],
        asia_preferred_currencies: ['JPY', 'AUD', 'NZD'],
        london_preferred_currencies: ['EUR', 'GBP', 'CHF'],
        new_york_preferred_currencies: ['USD', 'CAD'],
        high_noise_symbols: ['XAUUSD'],
        session_scores: { london_new_york_overlap: 1.0, london: 0.85, new_york: 0.8, asia: 0.6, off_session: 0.2, rollover_low_liquidity: 0.1, weekend: 0.0, friday_close_risk: 0.3 },
        log_each_check: false,
      },
      market_regime: {
        enabled: true, mode: 'shadow',
        bars: 200, atr_period: 14, long_window: 50, adx_period: 14,
        efficiency_window: 20, entropy_window: 20,
        compression_threshold: 0.3, expansion_threshold: 0.7,
        trend_adx_threshold: 25, range_adx_threshold: 20,
        panic_atr_percentile: 0.95, log_each_check: false,
      },
      volatility_engine: {
        enabled: true, mode: 'block',
        block_states: ['panic', 'compressed'],
        bars: 100, atr_period: 14, short_window: 10, long_window: 50,
        compression_threshold: 0.3, expansion_threshold: 0.7,
        panic_percentile: 0.95, min_range_to_atr: 0.3, log_each_check: false,
      },
      macro_flow: {
        enabled: true, mode: 'shadow',
        aggregation: 'weighted', timeframes: ['H1', 'H4', 'D1'],
        bars: 100, ema_fast: 8, ema_slow: 21, atr_period: 14, momentum_bars: 5,
        min_score: 0.3,
        weights: { H1: 0.5, H4: 1.0, D1: 1.5 },
        currency_strength: { enabled: true, weight: 0.3, min_score: 0.2 },
        log_each_check: false, reason_code: 'MACRO_FLOW',
      },
      portfolio_correlation: {
        enabled: true, mode: 'block',
        matrix_path: './data/correlation_matrix.csv',
        min_abs_correlation: 0.7, min_loss_money: 5,
        position_scope: 'system',
        log_passed_filter: false, block_same_risk_direction: true,
        reason_code: 'PORTFOLIO_CORR',
        reversal_relief: {
          enabled: false, mode: 'allow', timeframes: ['H1', 'H4'],
          min_confirmations: 2, require_candle_confirmation: true,
        },
      },
    },
    strategies: {
      strategy1: { enabled: true, invert_signal: false, magic_base: 20240001, legacy_magics: [], max_positions_per_symbol: 1, max_positions_per_side: 1, max_positions_mode: 'any_direction', max_positions_scope: 'strategy', cooldown_seconds: 60, use_tp_sl: true, tp_points: 60, sl_points: 30 },
      strategy2: { enabled: true, invert_signal: false, magic_base: 20240002, legacy_magics: [], max_positions_per_symbol: 2, max_positions_per_side: 1, max_positions_mode: 'by_direction', max_positions_scope: 'strategy', cooldown_seconds: 120, features_path: './data/features/s2.parquet', min_entries: 30, min_win_rate: 0.52, min_score: 0.55, target_preference: 1, use_feature_tp_sl: true, use_feature_sl: true, default_tp_points: 60, default_sl_points: 30 },
      strategy3: { enabled: false, invert_signal: false, magic_base: 20240003, legacy_magics: [], max_positions_per_symbol: 2, max_positions_per_side: 1, max_positions_mode: 'by_direction', max_positions_scope: 'strategy', cooldown_seconds: 180, features_path: './data/features/s3.parquet', min_entries: 30, min_win_rate: 0.52, min_score: 0.55, target_preference: 1, use_feature_tp_sl: true, use_feature_sl: true, default_tp_points: 60, default_sl_points: 30, use_exposure_groups: true, exposure_groups: {} },
      strategy4: { enabled: false, invert_signal: false, magic_base: 20240004, legacy_magics: [], max_positions_per_symbol: 1, max_positions_per_side: 1, max_positions_mode: 'any_direction', max_positions_scope: 'strategy', cooldown_seconds: 60, log_setup_details: false, symbol: 'EURUSD', broker_symbol: 'EURUSD', only_buy: false, setup: 'pullback', rule: 'ema_cross', ema_alignment: { enabled: true, periods: [9, 21, 50], buy_rule: 'ascending' }, use_tp_sl: true, sl_points: 30 },
      strategy5: { enabled: false, invert_signal: false, magic_base: 20240005, legacy_magics: [], max_positions_per_symbol: 2, max_positions_per_side: 1, max_positions_mode: 'by_direction', max_positions_scope: 'strategy', cooldown_seconds: 120, use_feature_tp_sl: true, use_feature_sl: true, default_tp_points: 60, default_sl_points: 30 },
      strategy6: { enabled: false, invert_signal: false, magic_base: 20240006, legacy_magics: [], max_positions_per_symbol: 2, max_positions_per_side: 1, max_positions_mode: 'by_direction', max_positions_scope: 'strategy', cooldown_seconds: 120, features_path: './data/features/s6.parquet', min_entries: 30, min_win_rate: 0.52, min_score: 0.55, target_preference: 1, enabled_experts: [], enabled_features: [], enabled_omnis_features: [], require_expert_confirmation: false, expert_min_confidence: 0.6, expert_min_score: 0.55, min_expert_votes: 1, require_feature_rule: false, log_each_loop: false, log_dir: './logs/s6', bars: 200, use_feature_tp_sl: true, tp_points: 60, sl_points: 30 },
    },
    trailing: {
      enabled: true,
      activation_pips: 20,
      distance_pips: 10,
      check_interval: 5,
      symbol_overrides: { XAUUSD: { activation_pips: 50, distance_pips: 25 } },
    },
    dashboard: {
      show_reason_column: true, show_reason_details: true, show_reason_summary: true,
      show_neutral_details: false, show_data_quality_details: false,
      show_market_structure_shadow: true, max_reason_items: 5, max_summary_items: 3,
    },
    event_bus: {
      event_log_enabled: true, event_log_dir: './logs/events',
      use_async: true, async_stop_timeout: 5,
      log_engine_results: false, log_tick_updates: false,
    },
    logging: {
      level: 'INFO', console_level: 'DEBUG', log_dir: './logs',
      max_file_size: 10485760, backup_count: 5,
    },
    currency_strength_map: {
      enabled: true, output_dir: './data/currency_strength',
      write_csv: true, write_json: true, wait_edge: 0.1,
      min_confidence_weight: 0.3, moderate_pair_score: 0.4, strong_pair_score: 0.65,
      timeframe_weights: { M5: 0.5, M15: 0.7, M30: 0.8, H1: 1.0, H4: 1.2, D1: 1.5 },
      false_neutral_detector: { enabled: true, mode: 'shadow', write_csv: false, min_pair_score: 0.5, min_aligned_timeframes: 2, structural_timeframes: ['H1', 'H4', 'D1'], require_structural_for_short_tf: true },
      directional_signal_guard: { enabled: true, mode: 'block', write_csv: false, min_confirm_score: 0.4, min_conflict_score: 0.6, reason_code: 'DIR_CONFLICT' },
    },
    operational_target_matrix: {
      enabled: true, mode: 'apply', update_on_startup: true, startup_mode: 'background',
      output_dir: './data/ots', lookback_days: 30, lookahead_minutes: 240,
      decision_filter: 'approved', market_time_offset_hours: -3,
      min_samples: 15, max_startup_seconds: 60,
      targets: [30, 40, 50, 60, 80, 100], stops: [15, 20, 25, 30],
      max_loss_streak: 3, min_win_rate: 0.50,
      use_mt5: true, save_mt5_history: true, latest_path: './data/ots/latest.json',
    },
    model: {
      model_dir: './models', global_model: 'fusion_global_v2.pkl',
      scaler: 'scaler.pkl', meta: 'meta.json',
      feature_columns: ['rsi', 'ema_slope', 'atr', 'volume_ratio', 'momentum'],
    },
    approved_ensembles: {
      enabled: true, registry_path: './data/ensembles/registry.json',
      tp_sl_report: './data/ensembles/tp_sl_report.json',
      min_member_weight: 0.1, min_score: 0.55, bars: 200,
    },
    ai_review_agent: {
      enabled: false, endpoint_url: 'http://localhost:8080/review',
      timeout_seconds: 10, fail_open: true, model_hint: 'gpt-4o',
      max_events: 20, auto_apply_changes: false,
    },
    ai_bridge: {
      enabled: false, host: 'localhost', port: 8080,
      provider: 'openai', model_hint: 'gpt-4o',
    },
    mt5_signal_panel: {
      enabled: true, use_common_files: true, output_dir: null, file_prefix: 'fusion_panel',
      refined_display: {
        enabled: true, show_final_row: true, require_operational_matrix: false,
        matrix_path: './data/ots/latest.json', min_samples: 10,
        require_recommended: false, block_on_missing_matrix: false,
        block_on_low_samples: false, block_on_missing_target_plan: false, keep_raw_reason: true,
      },
    },
    mt5_trade_zones: {
      enabled: true, use_common_files: true, output_dir: null, file_prefix: 'fusion_zones',
      bars: 200, sr_lookback: 50, atr_period: 14,
      entry_atr_width: 0.5, sr_atr_width: 1.0, sl_atr_multiplier: 1.5, tp_r_multiple: 2.0,
    },
    mt5_decision_layers: {
      enabled: false, use_common_files: true, output_dir: null, file_prefix: 'fusion_layers',
    },
    contracts: {
      overrides: [
        { symbol: 'XAUUSD', broker_symbol: 'GOLD', asset_type: 'commodity' },
        { symbol: 'BTCUSD', broker_symbol: 'BTCUSD', asset_type: 'crypto' },
      ],
    },
    oms: {
      snapshot_enabled: true, snapshot_dir: './data/oms_snapshots',
      trade_history_lookback_hours: 24,
    },
    runtime: {
      trading: {
        max_positions: 5, max_positions_per_symbol: 2,
        max_daily_loss_money: 300, max_floating_loss_money: 200,
      },
      signals: {
        buy_threshold: 0.55, sell_threshold: 0.55,
        confidence_filter: 0.60, min_signal_strength: 0.50,
      },
      filters: {
        block_top_bottom_without_breakout: false,
        portfolio_exposure_mode: 'block', portfolio_correlation_mode: 'block',
        market_briefing_mode: 'block', market_regime_mode: 'shadow',
        volatility_engine_mode: 'block', session_context_mode: 'block',
        macro_flow_mode: 'shadow', market_structure_mode: 'off',
        opportunity_engine_mode: 'off', execution_engine_mode: 'block',
        entry_timing_mode: 'shadow', risk_engine_mode: 'block',
        ema_alignment_mode: 'shadow', context_engine_mode: 'off',
        context_brain_mode: 'off', ema_lower_timeframes_direction_mode: 'shadow',
        candle_price_confirmation_mode: 'block', market_alignment_mode: 'block',
        timeframe_consensus_mode: 'block',
        market_alignment_block_states: ['bear', 'choppy'],
        timeframe_consensus_block_states: ['conflict'],
      },
      global_tp_sl: {
        use_runtime_override: false, tp_points: 60, sl_points: 30,
      },
      symbol_tp_sl: {
        XAUUSD: { tp_points: 150, sl_points: 75 },
        EURUSD: { tp_points: 60, sl_points: 30 },
      },
      risk_by_symbol: {
        EURUSD: { allow_new_orders: true, max_positions: 2, trailing_activation_points: 20, trailing_distance_points: 10 },
        XAUUSD: { allow_new_orders: true, max_positions: 1, trailing_activation_points: 50, trailing_distance_points: 25 },
      },
      symbols: {
        mode: 'include',
        include: ['EURUSD', 'GBPUSD', 'USDJPY', 'XAUUSD', 'AUDCAD', 'GBPJPY'],
        exclude: ['BTCUSD'],
      },
      symbol_timeframe_policies: {
        default: {
          signals: { buy_threshold: 0.55, sell_threshold: 0.55, confidence_filter: 0.60, min_signal_strength: 0.50 },
          filters: { required_filters: ['market_alignment', 'timeframe_consensus', 'session_context'], soft_filters: ['macro_flow', 'market_regime'] },
        },
        'GBPJPY.default': { signals: { buy_threshold: 0.62, sell_threshold: 0.62, confidence_filter: 0.65, min_signal_strength: 0.58 }, filters: { required_filters: ['market_alignment', 'volatility_engine'], soft_filters: [] } },
        'GBPJPY.H1': { signals: { buy_threshold: 0.60, sell_threshold: 0.60, confidence_filter: 0.63, min_signal_strength: 0.55 }, filters: { required_filters: ['market_alignment'], soft_filters: ['macro_flow'] } },
        'GBPJPY.M30': { signals: { buy_threshold: 0.65, sell_threshold: 0.65, confidence_filter: 0.68, min_signal_strength: 0.60 }, filters: { required_filters: ['market_alignment', 'timeframe_consensus'], soft_filters: [] } },
        'EURUSD.default': { signals: { buy_threshold: 0.55, sell_threshold: 0.55, confidence_filter: 0.60, min_signal_strength: 0.50 }, filters: { required_filters: ['market_alignment', 'timeframe_consensus'], soft_filters: ['macro_flow'] } },
        'EURUSD.H1': { signals: { buy_threshold: 0.57, sell_threshold: 0.57, confidence_filter: 0.62, min_signal_strength: 0.52 }, filters: { required_filters: ['market_alignment'], soft_filters: [] } },
        'GBPUSD.default': { signals: { buy_threshold: 0.58, sell_threshold: 0.58, confidence_filter: 0.63, min_signal_strength: 0.53 }, filters: { required_filters: ['market_alignment', 'session_context'], soft_filters: ['macro_flow'] } },
        'XAUUSD.default': { signals: { buy_threshold: 0.65, sell_threshold: 0.65, confidence_filter: 0.70, min_signal_strength: 0.60 }, filters: { required_filters: ['market_alignment', 'volatility_engine', 'session_context'], soft_filters: [] } },
        'AUDNZD.H4': { signals: { buy_threshold: 0.60, sell_threshold: 0.60, confidence_filter: 0.65, min_signal_strength: 0.55 }, filters: { required_filters: ['market_alignment'], soft_filters: [] } },
        'EURGBP.H4': { signals: { buy_threshold: 0.60, sell_threshold: 0.60, confidence_filter: 0.65, min_signal_strength: 0.55 }, filters: { required_filters: ['market_alignment'], soft_filters: [] } },
      },
    },
  };
}

export function mockFusionConfigSchema() {
  return {
    type: 'object',
    properties: {
      enabled: { type: 'boolean' },
      symbols: { type: 'array', items: { type: 'string' } },
      trading: { type: 'object' },
      risk: { type: 'object' },
      signal: { type: 'object' },
    },
  };
}