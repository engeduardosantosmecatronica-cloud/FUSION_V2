from __future__ import annotations

import ast
import csv
import hashlib
import re
from difflib import SequenceMatcher
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parents[1]
OLD_REPORT = PROJECT_DIR / "reports" / "expert_file_analysis" / "expert_files_analysis.csv"
ROOT_EXPERTS = PROJECT_DIR / "experts"
OUT_DIR = PROJECT_DIR / "reports" / "expert_file_analysis"


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def normalize_code(text: str) -> str:
    text = re.sub(r'""".*?"""', "", text, flags=re.S)
    text = re.sub(r"'''.*?'''", "", text, flags=re.S)
    text = re.sub(r"#.*", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def ast_names(text: str) -> tuple[list[str], list[str]]:
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return [], []
    classes: list[str] = []
    funcs: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            classes.append(node.name)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            funcs.append(node.name)
    return sorted(set(classes)), sorted(set(funcs))


def load_old_rows() -> list[dict[str, str]]:
    if not OLD_REPORT.exists():
        raise FileNotFoundError(f"Relatorio antigo nao encontrado: {OLD_REPORT}")
    with OLD_REPORT.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def root_inventory() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for path in sorted(ROOT_EXPERTS.glob("*.py")):
        text = read_text(path)
        norm = normalize_code(text)
        classes, funcs = ast_names(text)
        rows.append(
            {
                "path": str(path.relative_to(PROJECT_DIR)),
                "name": path.name,
                "sha256": sha256(text),
                "norm_sha256": sha256(norm),
                "classes": ",".join(classes),
                "functions": ",".join(funcs),
                "func_count": str(len(funcs)),
                "class_count": str(len(classes)),
                "lines": str(text.count("\n") + 1),
                "normalized_code": norm,
            }
        )
    return rows


def token_overlap(a: str, b: str) -> float:
    left = {token for token in re.split(r"\W+", a.lower()) if len(token) > 2}
    right = {token for token in re.split(r"\W+", b.lower()) if len(token) > 2}
    if not left or not right:
        return 0.0
    return len(left & right) / len(left | right)


def classify(root_name: str, old_row: dict[str, str], similarity: float, overlap: float) -> str:
    old_expert = (old_row.get("expert") or old_row.get("name") or "").lower()
    name = root_name.lower()
    if similarity >= 0.95:
        return "quase_duplicado"
    if similarity >= 0.75 or overlap >= 0.55:
        return "fortemente_relacionado"
    if old_expert and old_expert in name:
        return "mesma_familia_nome"
    return "baixo_relacionamento"


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    old_rows = load_old_rows()
    root_rows = root_inventory()

    old_enriched: list[dict[str, str]] = []
    for row in old_rows:
        path = PROJECT_DIR / row["path"]
        text = read_text(path) if path.exists() else ""
        norm = normalize_code(text)
        enriched = dict(row)
        enriched["normalized_code"] = norm
        old_enriched.append(enriched)

    comparison_rows: list[dict[str, str]] = []
    for root in root_rows:
        best: dict[str, str] | None = None
        best_similarity = -1.0
        best_overlap = 0.0
        for old in old_enriched:
            similarity = SequenceMatcher(None, root["normalized_code"], old["normalized_code"]).ratio()
            overlap = token_overlap(root["normalized_code"], old["normalized_code"])
            score = max(similarity, overlap)
            if score > max(best_similarity, best_overlap):
                best = old
                best_similarity = similarity
                best_overlap = overlap
        assert best is not None
        comparison_rows.append(
            {
                "root_path": root["path"],
                "root_name": root["name"],
                "root_classes": root["classes"],
                "root_functions": root["functions"],
                "closest_old_path": best["path"],
                "closest_old_name": best["name"],
                "closest_old_family": best.get("family", ""),
                "closest_old_expert": best.get("expert", ""),
                "closest_old_classes": best.get("classes", ""),
                "closest_old_functions": best.get("functions", ""),
                "sequence_similarity": f"{best_similarity:.4f}",
                "token_overlap": f"{best_overlap:.4f}",
                "classification": classify(root["name"], best, best_similarity, best_overlap),
            }
        )

    inventory_path = OUT_DIR / "root_experts_inventory.csv"
    compare_path = OUT_DIR / "root_vs_system_experts_comparison.csv"

    inventory_fields = [
        "path",
        "name",
        "sha256",
        "norm_sha256",
        "classes",
        "functions",
        "func_count",
        "class_count",
        "lines",
    ]
    with inventory_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=inventory_fields)
        writer.writeheader()
        for row in root_rows:
            writer.writerow({key: row[key] for key in inventory_fields})

    compare_fields = list(comparison_rows[0].keys()) if comparison_rows else []
    with compare_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=compare_fields)
        writer.writeheader()
        writer.writerows(comparison_rows)

    print(f"Root experts: {len(root_rows)}")
    print(f"System expert files: {len(old_rows)}")
    print(f"Inventory: {inventory_path}")
    print(f"Comparison: {compare_path}")


if __name__ == "__main__":
    main()
