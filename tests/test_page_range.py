from __future__ import annotations

import pytest

from anm.tools.page_range import parse_page_range


def test_single_page() -> None:
    assert parse_page_range("3", total_pages=10) == [2]


def test_page_range() -> None:
    assert parse_page_range("2-4", total_pages=10) == [1, 2, 3]


def test_comma_separated() -> None:
    assert parse_page_range("1,3,5", total_pages=10) == [0, 2, 4]


def test_mixed_ranges_and_singles() -> None:
    assert parse_page_range("1-3,5,8-10", total_pages=10) == [0, 1, 2, 4, 7, 8, 9]


def test_deduplicates_and_sorts() -> None:
    assert parse_page_range("3,1-3", total_pages=10) == [0, 1, 2]


def test_whitespace_is_stripped() -> None:
    assert parse_page_range(" 1 - 3 , 5 ", total_pages=10) == [0, 1, 2, 4]


def test_out_of_range_raises() -> None:
    with pytest.raises(ValueError, match="out of range"):
        parse_page_range("11", total_pages=10)


def test_zero_page_raises() -> None:
    with pytest.raises(ValueError, match="out of range"):
        parse_page_range("0", total_pages=10)


def test_negative_page_raises() -> None:
    with pytest.raises(ValueError, match="Invalid"):
        parse_page_range("-1", total_pages=10)


def test_empty_string_raises() -> None:
    with pytest.raises(ValueError, match="empty"):
        parse_page_range("", total_pages=10)


def test_reversed_range_raises() -> None:
    with pytest.raises(ValueError, match="Invalid range"):
        parse_page_range("5-3", total_pages=10)


def test_all_keyword() -> None:
    assert parse_page_range("all", total_pages=3) == [0, 1, 2]
