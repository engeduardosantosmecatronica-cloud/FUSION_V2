# AGENTS.md

Este diretório contém o dashboard local do Fusion Control Center.

- Preserve a integração local com tools/mt5_live_api.py.
- Não adicione autenticação ou serviços externos sem solicitação explícita.
- Use npm run build para validar alterações.
- Dados de mercado e ordens devem vir do backend Fusion; configurações auxiliares podem usar armazenamento local.
- Nunca coloque credenciais do MT5 no frontend.