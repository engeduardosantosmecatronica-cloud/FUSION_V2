from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


DEFAULT_IGNORED_DIRS = {"__pycache__", ".git", ".vscode", ".idea", "venv", ".venv"}
DEFAULT_IGNORED_FILES = {".DS_Store", "desktop.ini"}
DEFAULT_TEXT_EXTENSIONS = {".py", ".yaml", ".yml", ".toml", ".txt", ".md", ".rst"}


@dataclass(frozen=True)
class ImportIssue:
    path: Path
    name: str
    status: str
    replacement: str | None = None


def generate_tree(
    root: str | Path,
    ignored_dirs: Iterable[str] = DEFAULT_IGNORED_DIRS,
    ignored_files: Iterable[str] = DEFAULT_IGNORED_FILES,
) -> list[str]:
    root = Path(root)
    ignored_dir_set = set(ignored_dirs)
    ignored_file_set = set(ignored_files)

    def walk(path: Path, prefix: str = "") -> list[str]:
        entries = sorted(
            item
            for item in path.iterdir()
            if item.name not in ignored_dir_set and item.name not in ignored_file_set
        )
        lines: list[str] = []
        for index, item in enumerate(entries):
            last = index == len(entries) - 1
            connector = "`-- " if last else "|-- "
            lines.append(f"{prefix}{connector}{item.name}")
            if item.is_dir():
                next_prefix = prefix + ("    " if last else "|   ")
                lines.extend(walk(item, next_prefix))
        return lines

    return [f"{root.name}/"] + walk(root)


def find_imported_names(path: str | Path, module_name: str) -> list[str]:
    try:
        source = Path(path).read_text(encoding="utf-8")
        tree = ast.parse(source)
    except (OSError, SyntaxError, UnicodeDecodeError):
        return []

    imported: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module == module_name:
            imported.extend(alias.name for alias in node.names)
    return imported


def audit_import_contract(
    root: str | Path,
    module_name: str,
    removed_names: Iterable[str] = (),
    renamed_names: dict[str, str] | None = None,
) -> list[ImportIssue]:
    root = Path(root)
    removed = set(removed_names)
    renamed = renamed_names or {}
    issues: list[ImportIssue] = []
    for path in root.rglob("*.py"):
        if any(part in DEFAULT_IGNORED_DIRS for part in path.parts):
            continue
        for name in find_imported_names(path, module_name):
            if name in removed:
                issues.append(ImportIssue(path=path, name=name, status="removed"))
            elif name in renamed:
                issues.append(ImportIssue(path=path, name=name, status="renamed", replacement=renamed[name]))
    return issues


def consolidate_source_snapshot(
    root: str | Path,
    output_path: str | Path,
    ignored_dirs: Iterable[str] = DEFAULT_IGNORED_DIRS,
    extensions: Iterable[str] = DEFAULT_TEXT_EXTENSIONS,
) -> Path:
    root = Path(root)
    output = Path(output_path)
    ignored = set(ignored_dirs)
    allowed = {ext.lower() for ext in extensions}
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8") as out:
        for path in sorted(root.rglob("*")):
            if not path.is_file() or path.suffix.lower() not in allowed:
                continue
            if any(part in ignored for part in path.relative_to(root).parts):
                continue
            rel = path.relative_to(root)
            out.write(f"\n{'=' * 80}\n")
            out.write(f"ARQUIVO: {rel}\n")
            out.write(f"{'=' * 80}\n\n")
            out.write(path.read_text(encoding="utf-8", errors="ignore"))
            out.write("\n")
    return output


def summarize_mt5_diagnostics(
    initialize_ok: bool,
    terminal_connected: bool | None = None,
    account_available: bool | None = None,
    trade_mode: int | str | None = None,
    order_check_retcode: int | None = None,
) -> dict[str, str | bool | int | None]:
    if not initialize_ok:
        status = "mt5_initialize_failed"
    elif terminal_connected is False:
        status = "terminal_disconnected"
    elif account_available is False:
        status = "account_unavailable"
    elif trade_mode not in (None, 3, "FULL", "TRADE_MODE_FULL"):
        status = "trading_restricted"
    elif order_check_retcode not in (None, 0):
        status = "order_check_failed"
    else:
        status = "ok"
    return {
        "status": status,
        "initialize_ok": initialize_ok,
        "terminal_connected": terminal_connected,
        "account_available": account_available,
        "trade_mode": trade_mode,
        "order_check_retcode": order_check_retcode,
    }
