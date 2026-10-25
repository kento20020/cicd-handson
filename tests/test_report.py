"""report.py（HTML 生成）のテスト。"""

import datetime
from pathlib import Path
from zoneinfo import ZoneInfoNotFoundError

import pytest

from sales_report import report
from sales_report.aggregate import Sale, load_sales
from sales_report.report import render_html

# テストで使う固定の時刻（UTC 13:30 は日本時間 22:30）
FIXED_UTC = datetime.datetime(2026, 10, 23, 13, 30, tzinfo=datetime.UTC)


@pytest.fixture
def sales(sample_csv: Path) -> list[Sale]:
    return load_sales(sample_csv)


def test_html_has_basic_structure(sales: list[Sale]) -> None:
    html = render_html(sales, generated_at=FIXED_UTC)
    assert html.startswith("<!DOCTYPE html>")
    assert '<html lang="ja">' in html
    assert '<meta charset="utf-8">' in html
    assert 'name="viewport"' in html
    assert "<script" not in html  # JavaScript は使わない


def test_html_contains_formatted_total(sales: list[Sale]) -> None:
    assert "11,400円" in render_html(sales, generated_at=FIXED_UTC)


def test_html_contains_each_month_and_its_total(sales: list[Sale]) -> None:
    html = render_html(sales, generated_at=FIXED_UTC)
    for month in ("2026-04", "2026-05", "2026-06"):
        assert month in html
    # 月別合計も表示される（金額の計算が壊れていたらここでも気づける）
    assert "3,800円" in html
    assert "4,400円" in html
    assert "3,200円" in html


def test_html_bars_are_relative_to_the_largest_month(sales: list[Sale]) -> None:
    html = render_html(sales, generated_at=FIXED_UTC)
    assert "width: 100.0%" in html  # 最大の月 (5月 4,400円)
    assert "width: 86.4%" in html  # 4月 3,800 / 4,400
    assert "width: 72.7%" in html  # 6月 3,200 / 4,400


def test_html_contains_top_products(sales: list[Sale]) -> None:
    html = render_html(sales, generated_at=FIXED_UTC)
    assert html.index("コーヒー豆") < html.index("紅茶") < html.index("マグカップ")
    assert "クッキー" not in html  # 4位は載らない


def test_html_escapes_user_text() -> None:
    evil = Sale(datetime.date(2026, 4, 1), "<script>alert(1)</script>", 1, 100)
    html = render_html([evil], title="<b>タイトル</b>", generated_at=FIXED_UTC)
    assert "<script>" not in html
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html
    assert "<b>タイトル</b>" not in html
    assert "&lt;b&gt;タイトル&lt;/b&gt;" in html


def test_footer_shows_local_when_github_sha_is_unset(
    sales: list[Sale], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("GITHUB_SHA", raising=False)
    assert "<code>local</code>" in render_html(sales, generated_at=FIXED_UTC)


def test_footer_shows_local_when_github_sha_is_empty(
    sales: list[Sale], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("GITHUB_SHA", "")
    assert "<code>local</code>" in render_html(sales, generated_at=FIXED_UTC)


def test_footer_shows_short_sha_when_github_sha_is_set(
    sales: list[Sale], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("GITHUB_SHA", "abcdef1234567890abcdef1234567890abcdef12")
    html = render_html(sales, generated_at=FIXED_UTC)
    assert "<code>abcdef1</code>" in html
    assert "abcdef12" not in html  # 8文字目以降は出さない


def test_footer_timestamp_is_converted_to_tokyo_time(sales: list[Sale]) -> None:
    html = render_html(sales, generated_at=FIXED_UTC)
    assert "2026-10-23 22:30 JST" in html


def test_naive_generated_at_is_treated_as_tokyo_time(sales: list[Sale]) -> None:
    naive = datetime.datetime(2026, 1, 2, 3, 4)
    assert "2026-01-02 03:04 JST" in render_html(sales, generated_at=naive)


def test_default_generated_at_uses_current_time(sales: list[Sale]) -> None:
    assert " JST" in render_html(sales)


def test_tokyo_timezone_falls_back_to_fixed_offset(
    sales: list[Sale], monkeypatch: pytest.MonkeyPatch
) -> None:
    """tz データベースが無い環境（例: Windows）でも、日本時間で表示できる。"""

    def raise_not_found(key: str) -> None:
        raise ZoneInfoNotFoundError(key)

    monkeypatch.setattr(report, "ZoneInfo", raise_not_found)
    assert "2026-10-23 22:30 JST" in render_html(sales, generated_at=FIXED_UTC)


def test_empty_sales_still_renders() -> None:
    html = render_html([], generated_at=FIXED_UTC)
    assert "0円" in html
    assert html.count("データがありません") == 2  # 月別とトップ3
