"""同梱の data/sales.csv が壊れていないかを確認するテスト。

GitHub Pages に公開されるレポートは data/sales.csv から作られます。
CSV を編集して形式を壊したら、公開前にここで CI が赤くなります。
"""

from pathlib import Path

from sales_report.aggregate import load_sales, total_revenue

SAMPLE = Path(__file__).resolve().parents[1] / "data" / "sales.csv"


def test_bundled_sample_data_is_valid() -> None:
    sales = load_sales(SAMPLE)
    assert len(sales) > 0
    assert total_revenue(sales) > 0
