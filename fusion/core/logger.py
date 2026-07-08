"""
FUSION_V2 - Sistema de Logging
==============================
Inspirado nos melhores padrÃµes de NEXUS e OMNIS
"""
import sys
import logging
import os
from pathlib import Path
from datetime import datetime
from typing import Optional
from logging.handlers import RotatingFileHandler

try:
    import yaml
except Exception:
    yaml = None


class WindowsSafeRotatingFileHandler(RotatingFileHandler):
    """Rotaciona logs sem derrubar o sistema quando o Windows trava o arquivo."""

    def doRollover(self):
        try:
            super().doRollover()
        except PermissionError:
            if self.stream:
                self.stream.close()
                self.stream = None
            current = Path(self.baseFilename)
            fallback = current.with_name(
                f"{current.stem}_{os.getpid()}_{datetime.now().strftime('%H%M%S')}{current.suffix}"
            )
            self.baseFilename = str(fallback)
            if not self.delay:
                self.stream = self._open()


class FusionLogger:
    """Logger centralizado com rotaÃ§Ã£o de arquivos e mÃºltiplos handlers."""
    
    _instances: dict = {}
    
    def __init__(self, name: str = "Fusion", log_dir: Optional[Path] = None):
        self.name = name
        self.logger = logging.getLogger(name)
        
        if log_dir is None:
            log_dir = Path(__file__).resolve().parent.parent.parent / "logs"
        
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        if not self.logger.handlers:
            self._setup_handlers()
    
    def _setup_handlers(self):
        log_file = self.log_dir / f"fusion_{datetime.now().strftime('%Y%m%d')}.log"
        cfg = self._logging_config()
        
        formatter = logging.Formatter(
            '%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        file_handler = WindowsSafeRotatingFileHandler(
            log_file,
            maxBytes=int(cfg.get("max_file_size", 10_485_760) or 10_485_760),
            backupCount=int(cfg.get("backup_count", 5) or 5),
            encoding='utf-8'
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
        console_handler = logging.StreamHandler(sys.stdout)
        console_level = str(cfg.get("console_level", "WARNING") or "WARNING").upper()
        console_handler.setLevel(getattr(logging, console_level, logging.WARNING))
        console_handler.setFormatter(formatter)
        
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
        self.logger.setLevel(logging.DEBUG)

    def _logging_config(self) -> dict:
        config_path = Path(__file__).resolve().parent.parent.parent / "config" / "fusion_config.yaml"
        if yaml is None or not config_path.exists():
            return {}
        try:
            with config_path.open("r", encoding="utf-8") as handle:
                data = yaml.safe_load(handle) or {}
            return data.get("logging", {}) or {}
        except Exception:
            return {}
    
    def debug(self, msg: str):
        self.logger.debug(msg)
    
    def info(self, msg: str):
        self.logger.info(msg)
    
    def warning(self, msg: str):
        self.logger.warning(msg)
    
    def error(self, msg: str, exc_info: bool = False):
        self.logger.error(msg, exc_info=exc_info)
    
    def critical(self, msg: str, exc_info: bool = False):
        self.logger.critical(msg, exc_info=exc_info)
    
    @classmethod
    def get(cls, name: str = "Fusion") -> 'FusionLogger':
        if name not in cls._instances:
            cls._instances[name] = cls(name)
        return cls._instances[name]


def get_logger(name: str = "Fusion") -> FusionLogger:
    return FusionLogger.get(name)
