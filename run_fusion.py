"""
FUSION_V2 - Entry Point Wrapper
Adiciona o diretório do projeto ao Python path
"""
import sys
from pathlib import Path

project_dir = Path(__file__).resolve().parent
sys.path.insert(0, str(project_dir))

from fusion.main import FusionV2

if __name__ == "__main__":
    fusion = FusionV2()
    fusion.run()