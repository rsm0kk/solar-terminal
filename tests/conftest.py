# -*- coding: utf-8 -*-
import sys
from pathlib import Path

# scripts/ 를 임포트 경로에 추가 (core, adapters)
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
