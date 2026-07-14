# Fusion Dashboard

Interface React local do Fusion Control Center, sem serviços externos.

## Requisitos

- Node.js
- Ambiente Python do Fusion em ../.venv
- MetaTrader 5 aberto e autenticado

## Executar

A partir da raiz do projeto, execute: .dashboardun_dashboard.ps1

O inicializador verifica ou inicia a API MT5 em http://127.0.0.1:5000 e executa o dashboard em http://127.0.0.1:5173.

## Build

Entre na pasta dashboard e execute npm install e npm run build.

## Integração

- src/lib/fusionApi.js: cliente HTTP do backend Fusion.
- tools/mt5_live_api.py: candles, ticks, ordens e estado do MT5.
- src/api/localDataClient.js: configurações e registros locais no navegador.