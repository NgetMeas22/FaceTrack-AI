"""Server-side pagination and query optimization utility for FaceTrack AI."""

from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Query


def paginate(
    query: Query,
    page: int = 1,
    page_size: int = 10,
    max_page_size: int = 100,
) -> Dict[str, Any]:
    """
    Execute efficient server-side pagination with count and bounds checking.
    
    Returns structured pagination dictionary:
    - items: list of models for the current page
    - total: total record count
    - page: current 1-based page number
    - page_size: number of items per page
    - total_pages: computed total pages
    - has_prev: boolean indicating previous page exists
    - has_next: boolean indicating next page exists
    - prev_page: int or None
    - next_page: int or None
    """
    page = max(1, int(page or 1))
    page_size = min(max_page_size, max(1, int(page_size or 10)))

    total = query.order_by(None).count()
    total_pages = max(1, (total + page_size - 1) // page_size)

    if page > total_pages and total > 0:
        page = total_pages

    offset = (page - 1) * page_size
    items = query.offset(offset).limit(page_size).all()

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
        "has_prev": page > 1,
        "has_next": page < total_pages,
        "prev_page": page - 1 if page > 1 else None,
        "next_page": page + 1 if page < total_pages else None,
    }

