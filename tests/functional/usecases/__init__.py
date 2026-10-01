"""Use-case orchestration modules (UC01..UC20). Importing ``ensure_loaded`` registers every case once."""

from __future__ import annotations

import importlib

_LOADED = False


def ensure_loaded() -> None:
    global _LOADED
    if _LOADED:
        return
    for n in range(1, 21):
        importlib.import_module(f"{__name__}.uc{n:02d}.orchestration")
    _LOADED = True
