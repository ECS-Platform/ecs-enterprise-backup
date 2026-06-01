"""Server-side pagination helpers for ECS list views."""

from __future__ import annotations

from math import ceil
from urllib.parse import urlencode


def paginate(items: list, page: int = 1, per_page: int = 10) -> dict:
    """Slice *items* and return pagination metadata for templates."""
    page = max(1, page)
    per_page = max(1, min(per_page, 100))
    total = len(items)
    pages = max(1, ceil(total / per_page)) if total else 1
    page = min(page, pages)
    start = (page - 1) * per_page
    end = start + per_page
    page_items = items[start:end]
    return {
        "items": page_items,
        "page": page,
        "per_page": per_page,
        "total": total,
        "pages": pages,
        "start": start + 1 if total else 0,
        "end": min(end, total),
        "has_prev": page > 1,
        "has_next": page < pages,
        "prev_page": page - 1 if page > 1 else 1,
        "next_page": page + 1 if page < pages else pages,
    }


def page_numbers(current: int, total_pages: int, window: int = 2) -> list[int]:
    if total_pages <= 1:
        return [1]
    nums = set()
    for p in range(max(1, current - window), min(total_pages, current + window) + 1):
        nums.add(p)
    nums.add(1)
    nums.add(total_pages)
    return sorted(nums)


def pagination_query(base_params: dict, page: int, per_page: int | None = None) -> str:
    params = dict(base_params)
    params["page"] = page
    if per_page is not None:
        params["per_page"] = per_page
    return urlencode(params)
