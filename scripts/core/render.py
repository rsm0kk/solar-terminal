# -*- coding: utf-8 -*-
"""HTML 빌드 — 템플릿에 dashboard.json 을 주입해 단일 파일을 찍어낸다."""
from __future__ import annotations

import datetime as dt
import json
import shutil
from pathlib import Path

from .config import OUT_DIR, ROOT
from .template import HTML

PLACEHOLDER = "/*__DATA__*/{}"


def render_html(payload: dict, out_dir: Path = OUT_DIR) -> Path:
    if PLACEHOLDER not in HTML:
        raise ValueError("템플릿에 데이터 주입 자리표시자가 없습니다")

    data = json.dumps(payload, ensure_ascii=False, separators=(",", ":"), default=str)
    # HTML 안에 </script> 가 들어가면 스크립트가 조기 종료된다
    data = data.replace("</", "<\\/")

    html = HTML.replace(PLACEHOLDER, data)

    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = dt.date.today().strftime("%Y%m%d")
    dated = out_dir / f"태양광_대시보드_{stamp}.html"
    dated.write_text(html, encoding="utf-8")

    latest = out_dir / "태양광_대시보드_최신.html"
    shutil.copyfile(dated, latest)

    # GitHub Pages 배포용 (저장소 루트 index.html)
    (ROOT / "index.html").write_text(html, encoding="utf-8")

    return dated
