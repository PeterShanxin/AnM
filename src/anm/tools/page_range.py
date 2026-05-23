from __future__ import annotations

import re


def parse_page_range(spec: str, *, total_pages: int) -> list[int]:
    """Parse a human page specification into sorted, deduplicated zero-based indices.

    Accepts: "1-3,5,8-10", "all", single pages "5", ranges "2-4".
    Pages are 1-based in the spec, returned as 0-based indices.
    """
    spec = spec.strip()
    if not spec:
        raise ValueError("Page specification is empty.")

    if spec.casefold() == "all":
        return list(range(total_pages))

    indices: set[int] = set()
    for segment in spec.split(","):
        segment = segment.strip()
        if not segment:
            continue
        match = re.fullmatch(r"(\d+)\s*-\s*(\d+)", segment)
        if match:
            start = int(match.group(1))
            end = int(match.group(2))
            if start > end:
                raise ValueError(f"Invalid range: {start}-{end} (start > end).")
            _validate_page(start, total_pages)
            _validate_page(end, total_pages)
            indices.update(range(start - 1, end))
        elif re.fullmatch(r"\d+", segment):
            page = int(segment)
            _validate_page(page, total_pages)
            indices.add(page - 1)
        else:
            raise ValueError(f"Invalid page specification segment: '{segment}'.")

    return sorted(indices)


def _validate_page(page: int, total_pages: int) -> None:
    if page < 1 or page > total_pages:
        raise ValueError(f"Page {page} is out of range (1-{total_pages}).")
