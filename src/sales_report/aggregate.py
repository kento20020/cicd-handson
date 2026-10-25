"""売上データの読み込みと集計。

標準ライブラリだけで動くようにしてあります（CI を速く、シンプルに保つため）。
"""

import csv
import datetime
from dataclasses import dataclass
from pathlib import Path

# CSV の1行目（ヘッダー）として期待する列名。順番も固定。
EXPECTED_HEADER = ["date", "product", "quantity", "unit_price"]


@dataclass(frozen=True)
class Sale:
    """売上1件分。frozen=True なので作成後に値を書き換えられない。"""

    date: datetime.date
    product: str
    quantity: int
    unit_price: int

    @property
    def amount(self) -> int:
        """この1件の売上金額（数量 × 単価）。"""
        return self.quantity * self.unit_price


def _parse_int(raw: str, label: str, line_no: int) -> int:
    """文字列を 0 以上の整数に変換する。ダメなら行番号つきの ValueError。"""
    try:
        value = int(raw.strip())
    except ValueError:
        raise ValueError(f"{line_no}行目: {label}が整数ではありません: {raw!r}") from None
    if value < 0:
        raise ValueError(f"{line_no}行目: {label}は 0 以上にしてください: {value}")
    return value


def _parse_row(row: dict[str, str], line_no: int) -> Sale:
    """CSV の1行（辞書）を Sale に変換する。"""
    raw_date = row["date"].strip()
    try:
        date = datetime.datetime.strptime(raw_date, "%Y-%m-%d").date()
    except ValueError:
        raise ValueError(
            f"{line_no}行目: 日付は YYYY-MM-DD 形式にしてください: {raw_date!r}"
        ) from None

    product = row["product"].strip()
    if not product:
        raise ValueError(f"{line_no}行目: 商品名が空です")

    quantity = _parse_int(row["quantity"], "数量", line_no)
    unit_price = _parse_int(row["unit_price"], "単価", line_no)
    return Sale(date=date, product=product, quantity=quantity, unit_price=unit_price)


def load_sales(path: str | Path) -> list[Sale]:
    """CSV（UTF-8）から売上を読み込む。

    ヘッダーは `date,product,quantity,unit_price`。
    不正な行があれば、行番号つきのメッセージで ValueError を送出する。
    """
    sales: list[Sale] = []
    try:
        # utf-8-sig: Excel が付ける BOM（先頭の目印）があっても、なくても読める
        with open(path, encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            if reader.fieldnames != EXPECTED_HEADER:
                raise ValueError(
                    "1行目: ヘッダーは " + ",".join(EXPECTED_HEADER) + " にしてください"
                )
            for row in reader:
                # reader.line_num は「ファイルの何行目まで読んだか」。ヘッダーが1行目。
                line_no = reader.line_num
                # 列が足りない行は値が None、多い行はキー None に余りが入る
                if None in row or any(value is None for value in row.values()):
                    raise ValueError(f"{line_no}行目: 列の数が正しくありません（4列必要です）")
                sales.append(_parse_row(row, line_no))
    except UnicodeDecodeError as e:
        raise ValueError(
            f"UTF-8 として読み込めません。UTF-8 で保存し直してください（{e.start} バイト目付近）"
        ) from e
    return sales


def total_revenue(sales: list[Sale]) -> int:
    """全期間の売上合計。"""
    return sum(sale.amount for sale in sales)


def monthly_totals(sales: list[Sale]) -> dict[str, int]:
    """月ごとの売上合計。キーは "YYYY-MM"、古い月から順に並べて返す。"""
    totals: dict[str, int] = {}
    for sale in sales:
        key = f"{sale.date.year:04d}-{sale.date.month:02d}"
        totals[key] = totals.get(key, 0) + sale.quantity * sale.unit_price
    return dict(sorted(totals.items()))


def top_products(sales: list[Sale], n: int = 3) -> list[tuple[str, int]]:
    """売上金額の多い順に上位 n 商品を返す。同額なら商品名の昇順。"""
    if n < 0:
        raise ValueError(f"n は 0 以上にしてください: {n}")
    revenue: dict[str, int] = {}
    for sale in sales:
        revenue[sale.product] = revenue.get(sale.product, 0) + sale.amount
    ranked = sorted(revenue.items(), key=lambda item: (-item[1], item[0]))
    return ranked[:n]
