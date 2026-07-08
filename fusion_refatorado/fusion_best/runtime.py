from __future__ import annotations

import io
import logging
import sys
import time
import traceback
from dataclasses import dataclass
from typing import Callable


RuntimeCallable = Callable[[], None]
Notifier = Callable[[str], None]


@dataclass
class RuntimeHooks:
    initialize: RuntimeCallable | None = None
    run_once: RuntimeCallable | None = None
    run_forever: RuntimeCallable | None = None
    shutdown: RuntimeCallable | None = None
    notify: Notifier | None = None


def ensure_utf8_stdio() -> None:
    if getattr(sys.stdout, "encoding", None) and sys.stdout.encoding.upper() != "UTF-8":
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="ignore")
    if getattr(sys.stderr, "encoding", None) and sys.stderr.encoding.upper() != "UTF-8":
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="ignore")


def configure_runtime_logging(
    log_path: str = "trading.log",
    logger_name: str = "Fusion",
    level: int = logging.INFO,
) -> logging.Logger:
    ensure_utf8_stdio()
    logger = logging.getLogger(logger_name)
    logger.setLevel(level)
    logger.handlers.clear()

    fmt = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    file_handler = logging.FileHandler(log_path, encoding="utf-8")
    file_handler.setFormatter(fmt)
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(fmt)

    logger.addHandler(file_handler)
    logger.addHandler(stream_handler)
    logger.propagate = False
    return logger


def validate_writable_dir(path: str = "logs") -> bool:
    from pathlib import Path
    import os

    target = Path(path)
    try:
        target.mkdir(parents=True, exist_ok=True)
    except Exception:
        return False
    return target.exists() and os.access(target, os.W_OK)


def safe_notify(notifier: Notifier | None, message: str, logger: logging.Logger | None = None) -> None:
    if notifier is None:
        return
    try:
        notifier(message)
    except Exception as exc:
        if logger:
            logger.warning("Falha ao enviar notificacao: %s", exc)


def run_runtime_loop(
    hooks: RuntimeHooks,
    logger: logging.Logger | None = None,
    refresh_seconds: int = 10,
    max_iterations: int | None = None,
) -> None:
    """Lifecycle shell extracted from OMNIS main.py without direct MT5 dependency."""
    log = logger or logging.getLogger("Fusion")
    notify = hooks.notify or (lambda _message: None)
    iterations = 0

    try:
        if hooks.initialize:
            hooks.initialize()
        notify("Fusion iniciado")

        if hooks.run_forever:
            hooks.run_forever()
            return

        if hooks.run_once is None:
            raise ValueError("RuntimeHooks precisa de run_once ou run_forever.")

        while max_iterations is None or iterations < max_iterations:
            hooks.run_once()
            iterations += 1
            if max_iterations is None or iterations < max_iterations:
                time.sleep(refresh_seconds)
    except KeyboardInterrupt:
        log.warning("Execucao interrompida pelo usuario.")
    except Exception as exc:
        log.critical("Erro critico no runtime Fusion: %s", exc)
        log.debug("Traceback completo:\n%s", traceback.format_exc())
        notify(f"ERRO CRITICO NO Fusion: {exc}")
        raise
    finally:
        if hooks.shutdown:
            hooks.shutdown()
        notify("Fusion parado")
