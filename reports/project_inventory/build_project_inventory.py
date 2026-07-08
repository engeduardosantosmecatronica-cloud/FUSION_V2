from __future__ import annotations

import csv
from pathlib import Path

ROOT = Path.cwd()
OUT = ROOT / "reports" / "project_inventory"
OUT.mkdir(parents=True, exist_ok=True)

CATEGORIES = {
    "runtime_robo": {"fusion", "fusion_refatorado", "config", "runtime", "logs", "mql5"},
    "runtime_entrypoints": {"run_fusion.py", "requirements.txt"},
    "paineis_controle": {"terminal_windows", "terminal_qt", "terminal_desktop", "dashboard", "frontend", "fusion-frontend"},
    "dados_treinamento": {"02_research", "data", "features"},
    "modelos": {"models", "models_research", "models_principal", "models_experts", "models_experts_v2", "models_expr"},
    "analises_relatorios": {"reports", "prints", "table_predictions.py", "extract_predictions.py", "tabela.txt", "tabela2.txt", "tabela_blocos.txt"},
    "ferramentas": {"tools"},
    "documentacao": {"docs", "README.md", "DIAGNOSTICO_STARTUP.md", "IMPLEMENTACAO_CACHE_FEATURES.md", "IMPLEMENTACAO_OTIMIZACAO_COMPLETA.md", "OTIMIZACAO_STARTUP.md", "OTIMIZACAO_TERMINAL_BRIDGE.md", "plan.md"},
    "backups_legado": {"_archive", "backups", "fusion_pro", "repositorio", "revisar"},
    "projetos_externos_integracoes": {"_external"},
    "ambiente_dependencias": {".venv", ".vscode", "node_modules", "package.json", "package-lock.json", "rustup-init.exe"},
    "experimentos_experts": set(),
}

PURPOSE = {
    "runtime_robo": "necessario ou usado pelo Fusion em tempo real",
    "runtime_entrypoints": "entrada e dependencias para executar o robo",
    "paineis_controle": "interfaces, terminais e bridges visuais",
    "dados_treinamento": "bases, parquet e features para treino/backtest",
    "modelos": "artefatos de modelos treinados ou candidatos",
    "analises_relatorios": "saidas analiticas, auditorias, CSVs, markdowns e prints",
    "ferramentas": "scripts utilitarios; misturam runtime, treino, analise e manutencao",
    "documentacao": "documentos humanos e planos",
    "backups_legado": "copias antigas ou versoes refatoradas nao usadas no runtime principal",
    "projetos_externos_integracoes": "repos/projetos externos e integracoes isoladas",
    "ambiente_dependencias": "ambiente local, IDE e dependencias instaladas",
    "experimentos_experts": "experimentos/experts fora do nucleo principal",
    "nao_classificado": "precisa revisao manual",
}


def classify(name: str) -> str:
    for category, names in CATEGORIES.items():
        if name in names:
            return category
    return "nao_classificado"

rows = []
for item in sorted(ROOT.iterdir(), key=lambda p: p.name.lower()):
    if item.name in {".git"}:
        continue
    category = classify(item.name)
    try:
        if item.is_dir():
            direct_files = sum(1 for p in item.iterdir() if p.is_file())
            direct_dirs = sum(1 for p in item.iterdir() if p.is_dir())
            size = ""
            kind = "dir"
        else:
            direct_files = ""
            direct_dirs = ""
            size = item.stat().st_size
            kind = "file"
        last_write = item.stat().st_mtime
    except OSError:
        direct_files = direct_dirs = size = last_write = ""
        kind = "unknown"
    rows.append({
        "name": item.name,
        "kind": kind,
        "category": category,
        "purpose": PURPOSE[category],
        "direct_files": direct_files,
        "direct_dirs": direct_dirs,
        "size_bytes_file_only": size,
        "recommended_action": "manter_na_raiz" if category in {"runtime_robo", "runtime_entrypoints"} else "separar_ou_referenciar",
    })

csv_path = OUT / "root_inventory.csv"
with csv_path.open("w", encoding="utf-8", newline="") as fh:
    writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
    writer.writeheader()
    writer.writerows(rows)

md_path = OUT / "root_inventory.md"
lines = [
    "# Inventario da raiz do projeto\n\n",
    "Este inventario separa os itens por funcao operacional. Ele nao move arquivos; serve como mapa seguro antes da migracao fisica.\n\n",
    "| Item | Tipo | Categoria | Acao sugerida |\n",
    "|---|---|---|---|\n",
]
for row in rows:
    lines.append(f"| `{row['name']}` | {row['kind']} | {row['category']} | {row['recommended_action']} |\n")
md_path.write_text("".join(lines), encoding="utf-8")

print(csv_path)
print(md_path)



