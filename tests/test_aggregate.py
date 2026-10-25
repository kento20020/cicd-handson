"""aggregate.py（読み込みと集計）のテスト。"""

import datetime
from pathlib import Path

import pytest

from sales_report.aggregate import (
    Sale,
    load_sales,
    monthly_totals,
    top_products,
    total_revenue,
)

HEADER = "date,product,quantity,unit_price\n"


def make_sale(product: str, quantity: int, unit_price: int, day: str = "2026-04-01") -> Sale:
    return Sale(datetime.date.fromisoformat(day), product, quantity, unit_price)


# ---------------------------------------------------------------- 読み込み
def test_load_sales_reads_all_rows(sample_csv: Path) -> None:
    sales = load_sales(sample_csv)
    assert len(sales) == 6
    assert sales[0] == Sale(datetime.date(2026, 4, 1), "コーヒー豆", 2, 1500)


def test_sale_amount_is_quantity_times_unit_price() -> None:
    assert make_sale("紅茶", 3, 800).amount == 2400


def test_load_sales_header_only_returns_empty_list(tmp_path: Path) -> None:
    path = tmp_path / "empty.csv"
    path.write_text(HEADER, encoding="utf-8")
    assert load_sales(path) == []


def test_load_sales_accepts_utf8_bom(tmp_path: Path) -> None:
    """Excel が付ける BOM 付き UTF-8 でも読める。"""
    path = tmp_path / "bom.csv"
    path.write_bytes(b"\xef\xbb\xbf" + (HEADER + "2026-04-01,紅茶,1,800\n").encode("utf-8"))
    assert len(load_sales(path)) == 1


def test_load_sales_strips_spaces_around_values(tmp_path: Path) -> None:
    path = tmp_path / "spaces.csv"
    path.write_text(HEADER + " 2026-04-01 , 紅茶 , 2 , 800 \n", encoding="utf-8")
    assert load_sales(path) == [Sale(datetime.date(2026, 4, 1), "紅茶", 2, 800)]


@pytest.mark.parametrize(
    ("body", "expected"),
    [
        pytest.param("2026-13-40,紅茶,1,800\n", "3行目", id="bad-date"),
        pytest.param("2026/04/01,紅茶,1,800\n", "3行目", id="slash-date"),
        pytest.param("2026-04-01,紅茶,abc,800\n", "3行目", id="quantity-not-int"),
        pytest.param("2026-04-01,紅茶,1,8.5\n", "3行目", id="price-not-int"),
        pytest.param("2026-04-01,紅茶,,800\n", "3行目", id="quantity-empty"),
        pytest.param("2026-04-01,紅茶,-1,800\n", "3行目", id="quantity-negative"),
        pytest.param("2026-04-01,紅茶,1,-800\n", "3行目", id="price-negative"),
        pytest.param("2026-04-01,   ,1,800\n", "3行目", id="product-empty"),
        pytest.param("2026-04-01,紅茶,1\n", "3行目", id="too-few-columns"),
        pytest.param("2026-04-01,紅茶,1,800,999\n", "3行目", id="too-many-columns"),
    ],
)
def test_load_sales_rejects_bad_rows_with_line_number(
    tmp_path: Path, body: str, expected: str
) -> None:
    """不正な行は ValueError。メッセージに行番号（ヘッダーが1行目）が入る。"""
    path = tmp_path / "bad.csv"
    # 2行目は正常、3行目に不正な行を置く
    path.write_text(HEADER + "2026-04-01,コーヒー豆,1,1500\n" + body, encoding="utf-8")
    with pytest.raises(ValueError, match=expected):
        load_sales(path)


def test_load_sales_error_names_the_first_data_line(tmp_path: Path) -> None:
    path = tmp_path / "bad.csv"
    path.write_text(HEADER + "2026-04-01,紅茶,x,800\n", encoding="utf-8")
    with pytest.raises(ValueError, match="2行目"):
        load_sales(path)


@pytest.mark.parametrize(
    "content",
    [
        pytest.param("", id="empty-file"),
        pytest.param("日付,商品,数量,単価\n2026-04-01,紅茶,1,800\n", id="japanese-header"),
        pytest.param("product,date,quantity,unit_price\n", id="wrong-order"),
    ],
)
def test_load_sales_rejects_wrong_header(tmp_path: Path, content: str) -> None:
    path = tmp_path / "bad_header.csv"
    path.write_text(content, encoding="utf-8")
    with pytest.raises(ValueError, match="1行目"):
        load_sales(path)


def test_load_sales_rejects_non_utf8_file(tmp_path: Path) -> None:
    """Excel の「CSV」(Shift_JIS/CP932) をそのまま渡したときの親切なエラー。"""
    path = tmp_path / "cp932.csv"
    path.write_bytes((HEADER + "2026-04-01,コーヒー豆,1,1500\n").encode("cp932"))
    with pytest.raises(ValueError, match="UTF-8"):
        load_sales(path)


# ---------------------------------------------------------------- 集計
def test_total_revenue(sample_csv: Path) -> None:
    assert total_revenue(load_sales(sample_csv)) == 11400


def test_total_revenue_of_empty_is_zero() -> None:
    assert total_revenue([]) == 0


def test_monthly_totals_values_and_order(sample_csv: Path) -> None:
    """月別合計は「数量 × 単価」の合計。キーは古い月から順に並ぶ。

    このテストは、monthly_totals の `*` を `+` に書き換えると必ず失敗する
    （例: 4月は 3800 のはずが 2303 になる）。
    """
    totals = monthly_totals(load_sales(sample_csv))
    assert totals == {"2026-04": 3800, "2026-05": 4400, "2026-06": 3200}
    assert list(totals) == ["2026-04", "2026-05", "2026-06"]


def test_monthly_totals_sorts_months_even_if_input_is_unordered() -> None:
    sales = [
        make_sale("紅茶", 1, 100, "2026-06-01"),
        make_sale("紅茶", 1, 100, "2026-04-01"),
        make_sale("紅茶", 1, 100, "2025-12-31"),
    ]
    assert list(monthly_totals(sales)) == ["2025-12", "2026-04", "2026-06"]


def test_monthly_totals_single_sale_uses_multiplication() -> None:
    """最小の例。3個 × 100円 = 300円（足し算なら 103 になってしまう）。"""
    assert monthly_totals([make_sale("紅茶", 3, 100)]) == {"2026-04": 300}


def test_monthly_totals_of_empty_is_empty() -> None:
    assert monthly_totals([]) == {}


def test_top_products_orders_by_revenue_desc(sample_csv: Path) -> None:
    assert top_products(load_sales(sample_csv)) == [
        ("コーヒー豆", 4500),
        ("紅茶", 4000),
        ("マグカップ", 2000),
    ]


def test_top_products_respects_n(sample_csv: Path) -> None:
    sales = load_sales(sample_csv)
    assert top_products(sales, n=1) == [("コーヒー豆", 4500)]
    assert len(top_products(sales, n=10)) == 4  # 商品は4種類しかない
    assert top_products(sales, n=0) == []


def test_top_products_breaks_ties_by_name_ascending() -> None:
    sales = [
        make_sale("b", 1, 100),
        make_sale("a", 1, 100),
        make_sale("c", 1, 50),
    ]
    assert top_products(sales, n=3) == [("a", 100), ("b", 100), ("c", 50)]
    assert top_products(sales, n=1) == [("a", 100)]


def test_top_products_sums_the_same_product_across_rows() -> None:
    sales = [make_sale("紅茶", 1, 800), make_sale("紅茶", 2, 800, "2026-05-01")]
    assert top_products(sales) == [("紅茶", 2400)]


def test_top_products_of_empty_is_empty() -> None:
    assert top_products([]) == []


def test_top_products_rejects_negative_n() -> None:
    with pytest.raises(ValueError, match="n は 0 以上"):
        top_products([], n=-1)
