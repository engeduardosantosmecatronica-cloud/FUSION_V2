from __future__ import annotations

import csv
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path.cwd()
OUT = ROOT / "reports" / "project_inventory"
OUT.mkdir(parents=True, exist_ok=True)

SKIP_DIRS = {
    ".git",
    ".venv",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "node_modules",
    "bin",
    "obj",
}

RUNTIME_TOP = {"fusion", "fusion_refatorado", "config", "mql5"}
PANELS_TOP = {"terminal_windows", "terminal_qt", "terminal_desktop", "dashboard", "frontend", "fusion-frontend"}
TRAINING_TOP = {"data", "features", "models", "models_research", "models_principal", "models_experts", "models_experts_v2", "models_expr", "02_research"}
ANALYSIS_TOP = {"reports"}
DOCS_TOP = {"docs"}
ARCHIVE_TOP = {"_archive"}
EXTERNAL_TOP = {"_external"}

ENTRYPOINT_FILES = {"run_fusion.py", "requirements.txt", "README.md", "package.json", "package-lock.json"}

RUNTIME_TOOLS_HINTS = (
    "mt5",
    "frontend",
    "quantedinger",
    "quanding",
    "live_api",
    "socket",
    "export_mt5_candles",
    "fusion_frontend_data",
    "open_fusion_frontend",
    "manage_mt5",
)

TRAINING_HINTS = (
    "train",
    "model",
    "features",
    "dataset",
    "parquet",
)

ANALYSIS_HINTS = (
    "analyze",
    "analysis",
    "backtest",
    "report",
    "summarize",
    "optimize",
    "drawdown",
    "inventory",
    "check",
    "validate",
    "smoke",
)


def should_skip_dir(path: Path) -> bool:
    return path.name in SKIP_DIRS


def classify(path: Path) -> tuple[str, str, str]:
    rel = path.relative_to(ROOT)
    parts = rel.parts
    top = parts[0]
    name = path.name.lower()
    rel_text = str(rel).replace("\\", "/").lower()

    if len(parts) == 1 and top in ENTRYPOINT_FILES:
        if top in {"run_fusion.py", "requirements.txt"}:
            return "runtime_entrypoint", "manter", "entrada/dependencia direta do robo"
        if top == "README.md":
            return "documentacao", "manter", "manual principal do projeto"
        return "ambiente_frontend", "revisar", "dependencia/configuracao JS da raiz"

    if top in RUNTIME_TOP:
        if top == "config":
            return "config_runtime", "manter_com_cautela", "configuracao operacional do Fusion"
        return "runtime_robo", "manter_com_cautela", "codigo ou artefato usado pelo runtime"

    if top in PANELS_TOP:
        return "painel_monitoramento", "manter_se_usado", "interface/painel/terminal de controle"

    if top == "tools":
        if any(hint in rel_text for hint in RUNTIME_TOOLS_HINTS):
            return "ferramenta_runtime_bridge", "manter_com_cautela", "script de bridge/API/runtime"
        if any(hint in rel_text for hint in TRAINING_HINTS):
            return "ferramenta_treinamento", "manter_se_usado", "script de treino/modelos/features"
        if any(hint in rel_text for hint in ANALYSIS_HINTS):
            return "ferramenta_analise_teste", "manter_se_usado", "script de analise/backtest/validacao"
        return "ferramenta_nao_classificada", "revisar", "script utilitario precisa revisao manual"

    if top in TRAINING_TOP:
        return "dados_modelos_treinamento", "manter_se_usado", "dados, features, modelos ou pesquisa"

    if top in ANALYSIS_TOP:
        if "project_inventory" in parts:
            return "inventario_projeto", "manter", "inventario gerado para organizacao"
        return "analise_relatorio", "manter_se_util", "saida de analise, backtest ou auditoria"

    if top in DOCS_TOP:
        return "documentacao", "manter_se_util", "documentacao operacional/tecnica"

    if top in ARCHIVE_TOP:
        return "arquivo_morto_legado", "candidato_remocao_apos_revisao", "backup ou legado isolado"

    if top in EXTERNAL_TOP:
        return "projeto_externo", "candidato_remocao_apos_revisao", "repositorio externo/integracao isolada"

    if top == "runtime":
        return "estado_runtime", "nao_deletar_com_robo_rodando", "estado vivo/cache/snapshots runtime"

    if top == "logs":
        return "logs", "pode_limpar_com_robo_parado", "logs gerados pelo sistema"

    if top in {".vscode"}:
        return "ambiente_ide", "manter_se_util", "configuracao local da IDE"

    if top == "rustup-init.exe":
        return "instalador_local", "candidato_remocao", "instalador baixado; nao e runtime do Fusion"

    return "nao_classificado", "revisar", "nao foi possivel classificar automaticamente"


def iter_files() -> tuple[list[Path], Counter[str]]:
    files: list[Path] = []
    skipped: Counter[str] = Counter()
    stack = [ROOT]
    while stack:
        current = stack.pop()
        try:
            children = sorted(current.iterdir(), key=lambda p: p.name.lower())
        except OSError:
            continue
        for child in children:
            if child.is_dir():
                if should_skip_dir(child):
                    skipped[str(child.relative_to(ROOT))] += 1
                    continue
                stack.append(child)
            elif child.is_file():
                files.append(child)
    return sorted(files, key=lambda p: str(p.relative_to(ROOT)).lower()), skipped


def main() -> None:
    files, skipped = iter_files()
    rows = []
    for path in files:
        rel = path.relative_to(ROOT)
        category, action, purpose = classify(path)
        try:
            size = path.stat().st_size
        except OSError:
            size = ""
        rows.append(
            {
                "path": str(rel).replace("\\", "/"),
                "top_level": rel.parts[0],
                "suffix": path.suffix.lower(),
                "category": category,
                "recommended_action": action,
                "purpose": purpose,
                "size_bytes": size,
            }
        )

    csv_path = OUT / "detailed_file_inventory.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()) if rows else [])
        writer.writeheader()
        writer.writerows(rows)

    by_top = defaultdict(list)
    by_category = Counter()
    by_action = Counter()
    for row in rows:
        by_top[row["top_level"]].append(row)
        by_category[row["category"]] += 1
        by_action[row["recommended_action"]] += 1

    md = []
    md.append("# Inventario detalhado de arquivos\n\n")
    md.append("Este inventario foi gerado para apoiar limpeza segura do projeto. O CSV contem a lista completa dos arquivos considerados.\n\n")
    md.append(f"- Arquivos inventariados: {len(rows)}\n")
    md.append(f"- CSV completo: `reports/project_inventory/detailed_file_inventory.csv`\n")
    md.append("- Diretorios pesados/gerados ignorados no inventario: `.git`, `.venv`, `node_modules`, `bin`, `obj`, caches Python/testes.\n\n")

    md.append("## Resumo por acao sugerida\n\n")
    md.append("| Acao | Arquivos |\n|---|---:|\n")
    for action, count in sorted(by_action.items()):
        md.append(f"| `{action}` | {count} |\n")

    md.append("\n## Resumo por categoria\n\n")
    md.append("| Categoria | Arquivos |\n|---|---:|\n")
    for category, count in sorted(by_category.items()):
        md.append(f"| `{category}` | {count} |\n")

    md.append("\n## Resumo por pasta da raiz\n\n")
    md.append("| Pasta/arquivo | Arquivos | Categorias principais | Acao dominante |\n|---|---:|---|---|\n")
    for top, top_rows in sorted(by_top.items()):
        cats = Counter(r["category"] for r in top_rows).most_common(3)
        acts = Counter(r["recommended_action"] for r in top_rows).most_common(1)
        cats_text = ", ".join(f"{cat} ({count})" for cat, count in cats)
        action_text = acts[0][0] if acts else ""
        md.append(f"| `{top}` | {len(top_rows)} | {cats_text} | `{action_text}` |\n")

    md.append("\n## Amostras por pasta\n\n")
    md.append("A lista completa esta no CSV. As amostras abaixo mostram os primeiros arquivos de cada area para orientar a revisao humana.\n\n")
    for top, top_rows in sorted(by_top.items()):
        md.append(f"### `{top}`\n\n")
        md.append("| Arquivo | Categoria | Acao |\n|---|---|---|\n")
        for row in top_rows[:40]:
            md.append(f"| `{row['path']}` | `{row['category']}` | `{row['recommended_action']}` |\n")
        if len(top_rows) > 40:
            md.append(f"| ... | mais {len(top_rows) - 40} arquivos no CSV | ... |\n")
        md.append("\n")

    md.append("## Diretorios ignorados por serem ambiente/cache\n\n")
    if skipped:
        for path in sorted(skipped):
            md.append(f"- `{path}/`\n")
    else:
        md.append("- nenhum\n")

    md_path = OUT / "detailed_file_inventory.md"
    md_path.write_text("".join(md), encoding="utf-8")

    print(csv_path)
    print(md_path)
    print(f"files={len(rows)}")


if __name__ == "__main__":
    main()
