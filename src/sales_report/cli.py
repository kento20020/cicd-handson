"""コマンドラインの入り口。

使い方:
    python -m sales_report --input data/sales.csv --output site/index.html
    sales-report --input data/sales.csv --output site/index.html   (インストール後)
"""

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from sales_report.aggregate import load_sales
from sales_report.report import render_html


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="sales-report",
        description="売上CSVから HTML レポートを作ります。",
    )
    parser.add_argument("--input", default="data/sales.csv", help="入力CSV（既定: data/sales.csv）")
    parser.add_argument(
        "--output", default="site/index.html", help="出力HTML（既定: site/index.html）"
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """レポートを作って終了コードを返す（0=成功, 1=入力エラー）。"""
    args = build_parser().parse_args(argv)

    try:
        sales = load_sales(args.input)
    except ValueError as e:
        print(f"エラー: {e}", file=sys.stderr)
        return 1
    except OSError as e:
        print(f"エラー: 入力ファイルを読み込めません: {e}", file=sys.stderr)
        return 1

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(render_html(sales), encoding="utf-8")
    print(output)
    return 0
