# FUSION_V2 pipelines

Presets operacionais para sair da extracao do BACKUP e entrar no treino controlado.

## Inventario consolidado

```powershell
python fusion_refatorado\pipelines\registry_inventory.py
```

## Modelo unico

```powershell
python fusion_refatorado\pipelines\train_single_model.py --input fusion_refatorado\data\omnis_backup\dados\dados_historicos\eurusd\EURUSD_M5.csv --symbol EURUSD --timeframe M5 --dry-run
```

Remova `--dry-run` para treinar e salvar em `fusion_refatorado\models\fusion_single`.

## Multiplos experts

```powershell
python fusion_refatorado\pipelines\train_experts.py --input fusion_refatorado\data\omnis_backup\dados\dados_historicos\eurusd\EURUSD_M5.csv --symbol EURUSD --timeframe M5 --experts trend,volatility,candles,orderflow,risk,sr,reversal,pullback,quant --dry-run
```

Remova `--dry-run` para treinar e salvar em `fusion_refatorado\models\fusion_experts`.

Para recriar apenas o relatorio consolidado a partir dos metadados ja salvos:

```powershell
python fusion_refatorado\pipelines\train_experts.py --input fusion_refatorado\data\omnis_backup\dados\dados_historicos\eurusd\EURUSD_M5.csv --symbol EURUSD --timeframe M5 --merge-existing-only
```

## Backtest e calibracao dos experts

```powershell
python fusion_refatorado\pipelines\backtest_fusion_experts.py --input fusion_refatorado\data\omnis_backup\dados\dados_historicos\eurusd\EURUSD_M5.csv --symbol EURUSD --timeframe M5 --oos-fraction 0.20 --min-confidence 0.55 --min-trades 30
```

Isso gera:

- `fusion_refatorado\reports\fusion_backtests\EURUSD\M5\expert_backtest_summary.csv`
- `fusion_refatorado\reports\fusion_backtests\EURUSD\M5\expert_backtest_trades.csv`
- `fusion_refatorado\reports\fusion_backtests\EURUSD\M5\calibrated_weights.json`

## Walk-forward temporal

```powershell
python fusion_refatorado\pipelines\walkforward_fusion_experts.py --input fusion_refatorado\data\omnis_backup\dados\dados_historicos\eurusd\EURUSD_M5.csv --symbol EURUSD --timeframe M5 --train-fraction 0.80 --min-confidence 0.55 --min-trades 30
```

Isso treina os experts nos primeiros 80% do historico e testa nos 20% finais. Tambem avalia o modo `NORMAL` e `INVERT` para experts direcionais.

Saidas principais:

- `fusion_refatorado\reports\fusion_walkforward\EURUSD\M5\walkforward_summary.csv`
- `fusion_refatorado\reports\fusion_walkforward\EURUSD\M5\walkforward_trades.csv`
- `fusion_refatorado\reports\fusion_walkforward\EURUSD\M5\walkforward_weights.json`
- `fusion_refatorado\models\fusion_walkforward\EURUSD\M5`

## Preset de ensemble

```powershell
python fusion_refatorado\pipelines\train_fusion_ensemble.py
```

Isso gera `fusion_refatorado\models\fusion_ensemble\ensemble_config.json` com candidatos iniciais. Os pesos devem ser recalibrados apos backtest out-of-sample.

Para aplicar pesos calibrados:

```powershell
python fusion_refatorado\pipelines\train_fusion_ensemble.py --calibration-report fusion_refatorado\reports\fusion_backtests\EURUSD\M5\calibrated_weights.json
```

Para gerar um ensemble separado com pesos walk-forward:

```powershell
python fusion_refatorado\pipelines\train_fusion_ensemble.py --calibration-report fusion_refatorado\reports\fusion_walkforward\EURUSD\M5\walkforward_weights.json --output fusion_refatorado\models\fusion_ensemble\ensemble_walkforward_config.json
```

## Lote de simbolos

```powershell
python fusion_refatorado\pipelines\run_symbol_batch.py --timeframe M5 --resume
```

O lote usa `data\parquet\M5\<SYMBOL>.parquet`, executa treino dos 9 experts, backtest, walk-forward e ensemble walk-forward por simbolo. O resumo consolidado dos simbolos solicitados fica em:

- `fusion_refatorado\reports\batch_runs\m5_requested_symbols_consolidated.csv`

## Selecao para staging/producao

```powershell
python fusion_refatorado\pipelines\select_production_candidates.py --symbols "EURUSD GBPUSD USDJPY GBPJPY AUDUSD USDCAD USDCHF EURGBP EURJPY NZDUSD EURCHF AUDCAD AUDCHF EURCAD GBPCHF AUDJPY CADCHF EURAUD GBPAUD NZDCAD AUDNZD CHFJPY EURNZD" --timeframe M5
```

Saidas:

- `fusion_refatorado\reports\production_selection\M5_production_candidates.csv`
- `fusion_refatorado\reports\production_selection\M5_production_candidates.json`
- `fusion_refatorado\models\production_registry\M5_approved_ensembles.json`
