# -*- coding: utf-8 -*-
"""HTTP 클라이언트: 재시도·지수백오프·캐싱·타임아웃·SSL 검사환경 대응."""
from __future__ import annotations

import hashlib
import json
import time
import urllib.parse
from pathlib import Path
from typing import Any, Optional

import requests
from requests.adapters import HTTPAdapter

from .config import CACHE_DIR

UA = "Mozilla/5.0 (compatible; SolarAnalystTerminal/1.0; +local-research-use)"
DEFAULT_TIMEOUT = 45

# 일부 PC는 백신·기업 프록시가 SSL 을 검사(중간자)해서 인증서 검증이 깨진다.
# 먼저 정상 검증을 시도하고, 검증 실패가 날 때만 그 호스트에 한해 검증을 끈다.
_INSECURE_HOSTS: set[str] = set()
_WARNED = False


class FetchError(RuntimeError):
    """수집 실패. 호출부는 이걸 잡아서 소스를 error 상태로 기록하고 계속 진행한다."""

    def __init__(self, message: str, status: Optional[int] = None):
        super().__init__(message)
        self.status = status


def _session() -> requests.Session:
    s = requests.Session()
    s.headers.update({"User-Agent": UA})
    s.mount("https://", HTTPAdapter(pool_maxsize=8))
    s.mount("http://", HTTPAdapter(pool_maxsize=8))
    return s


_SESSION = _session()


def _cache_path(url: str, suffix: str = ".bin") -> Path:
    h = hashlib.sha1(url.encode("utf-8")).hexdigest()[:16]
    host = urllib.parse.urlparse(url).netloc.replace(":", "_")
    return CACHE_DIR / f"{host}_{h}{suffix}"


def _cache_read(path: Path, ttl_sec: int) -> Optional[bytes]:
    if ttl_sec <= 0 or not path.exists():
        return None
    if time.time() - path.stat().st_mtime > ttl_sec:
        return None
    try:
        return path.read_bytes()
    except Exception:
        return None


def fetch(
    url: str,
    *,
    params: Optional[dict[str, Any]] = None,
    timeout: int = DEFAULT_TIMEOUT,
    retries: int = 3,
    cache_ttl: int = 0,
    headers: Optional[dict[str, str]] = None,
    stream_to: Optional[Path] = None,
) -> bytes:
    """URL 을 가져온다. 실패하면 FetchError.

    cache_ttl : 초. 0 이면 캐시 미사용.
    stream_to : 지정하면 대용량 파일을 그 경로로 스트리밍 저장하고 경로 bytes 대신
                파일 내용을 반환하지 않는다(빈 bytes 반환). 캐시와 함께 쓴다.
    """
    global _WARNED

    full = url
    if params:
        full = url + ("&" if "?" in url else "?") + urllib.parse.urlencode(params, safe=":/")

    cpath = _cache_path(full)
    if cache_ttl > 0:
        cached = _cache_read(cpath, cache_ttl)
        if cached is not None:
            return cached

    host = urllib.parse.urlparse(full).netloc
    verify = host not in _INSECURE_HOSTS
    last_err = ""
    last_status: Optional[int] = None

    for attempt in range(retries + 1):
        try:
            resp = _SESSION.get(
                full,
                timeout=timeout,
                verify=verify,
                headers=headers,
                stream=bool(stream_to),
            )
            last_status = resp.status_code

            # rate limit / 일시 장애 → 백오프 후 재시도
            if resp.status_code in (429, 500, 502, 503, 504):
                retry_after = resp.headers.get("Retry-After")
                wait = float(retry_after) if (retry_after or "").isdigit() else 1.5 * (2**attempt)
                last_err = f"HTTP {resp.status_code}"
                if attempt < retries:
                    time.sleep(min(wait, 20))
                    continue
                raise FetchError(f"{last_err}: {resp.text[:200]}", resp.status_code)

            resp.raise_for_status()

            if stream_to:
                stream_to.parent.mkdir(parents=True, exist_ok=True)
                with stream_to.open("wb") as f:
                    for chunk in resp.iter_content(chunk_size=1 << 20):
                        if chunk:
                            f.write(chunk)
                return b""

            data = resp.content
            if cache_ttl > 0:
                try:
                    cpath.write_bytes(data)
                except Exception:
                    pass
            return data

        except requests.exceptions.SSLError as e:
            # 이 호스트만 검증을 끄고 즉시 재시도 (다른 호스트엔 영향 없음)
            if verify:
                _INSECURE_HOSTS.add(host)
                verify = False
                if not _WARNED:
                    _WARNED = True
                    print(
                        "  [주의] SSL 인증서 검증 실패 — 이 PC의 보안 프로그램이 SSL 트래픽을 "
                        "검사 중으로 보입니다. 해당 호스트에 한해 검증 없이 재시도합니다.",
                        flush=True,
                    )
                    # 위에서 한 번 알렸으므로 호출마다 반복되는 urllib3 경고는 끈다
                    try:
                        import urllib3
                        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
                    except Exception:
                        pass
                continue
            last_err = f"SSL: {str(e)[:150]}"
        except requests.exceptions.HTTPError as e:
            code = e.response.status_code if e.response is not None else None
            body = e.response.text[:200] if e.response is not None else ""
            raise FetchError(f"HTTP {code}: {body}", code) from None
        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
            last_err = f"{type(e).__name__}: {str(e)[:120]}"
        except Exception as e:
            last_err = f"{type(e).__name__}: {str(e)[:120]}"

        if attempt < retries:
            time.sleep(1.2 * (2**attempt))

    raise FetchError(last_err or "알 수 없는 실패", last_status)


def fetch_json(url: str, **kw) -> Any:
    raw = fetch(url, **kw)
    try:
        return json.loads(raw.decode("utf-8", "replace"))
    except json.JSONDecodeError as e:
        raise FetchError(f"JSON 파싱 실패: {e} / 앞부분: {raw[:200]!r}") from None


def fetch_text(url: str, encoding: str = "utf-8", **kw) -> str:
    return fetch(url, **kw).decode(encoding, "replace")


def download_cached(url: str, dest: Path, ttl_sec: int) -> Path:
    """대용량 파일을 dest 에 받아둔다. ttl 이내면 재다운로드하지 않는다."""
    if dest.exists() and (time.time() - dest.stat().st_mtime) < ttl_sec:
        return dest
    fetch(url, stream_to=dest, timeout=180, retries=2)
    return dest
