"""
Build info del dashboard — commit hash + fecha del último deploy.

Prioridad de fuentes (primera disponible gana):
  1. Variables de entorno `GIT_COMMIT` / `GIT_COMMIT_DATE` (útil si en algún
     momento se mete CI o se quiere overridear desde Streamlit Cloud secrets).
  2. `git rev-parse --short HEAD` + `git log -1 --format=%cI` ejecutados en
     runtime sobre el repo clonado por Streamlit Cloud.
  3. Fallback `"dev"` cuando ninguna de las dos anteriores está disponible
     (entorno sin git, o ejecución desde un tarball).

El resultado se cachea con `lru_cache`: como el proceso Python se reinicia
en cada redeploy de Streamlit Cloud, el valor cacheado siempre refleja la
versión publicada actual — no requiere invalidación manual.
"""
from __future__ import annotations

import os
import subprocess
from datetime import datetime
from functools import lru_cache
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
_FALLBACK_COMMIT = "dev"


def _run_git(args: list[str]) -> str:
    return subprocess.check_output(
        ["git", *args],
        cwd=_REPO_ROOT,
        stderr=subprocess.DEVNULL,
        timeout=2,
    ).decode().strip()


@lru_cache(maxsize=1)
def get_build_info() -> dict[str, str]:
    """
    Devuelve `{"commit": "<7-char hash>", "date": "YYYY-MM-DD HH:MM", "source": "..."}`.

    `source` indica de dónde salió la info — útil para debug en Streamlit Cloud
    si la fecha o el commit aparecen vacíos.
    """
    commit_env = os.environ.get("GIT_COMMIT", "").strip()
    if commit_env:
        return {
            "commit": commit_env[:7],
            "date": os.environ.get("GIT_COMMIT_DATE", "").strip(),
            "source": "env",
        }

    try:
        commit = _run_git(["rev-parse", "--short", "HEAD"])
        date_iso = _run_git(["log", "-1", "--format=%cI"])
        try:
            dt = datetime.fromisoformat(date_iso)
            date = dt.strftime("%Y-%m-%d %H:%M")
        except ValueError:
            date = date_iso[:16]
        return {"commit": commit, "date": date, "source": "git"}
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired,
            FileNotFoundError, OSError):
        return {"commit": _FALLBACK_COMMIT, "date": "", "source": "fallback"}


def get_version_string() -> str:
    """Texto compacto listo para sidebar/footer. Ej: 'b50cba2 · 2026-05-19 14:15'."""
    info = get_build_info()
    if info["commit"] == _FALLBACK_COMMIT:
        return "dev"
    if info["date"]:
        return f"{info['commit']} · {info['date']}"
    return info["commit"]
