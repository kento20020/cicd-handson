"""売上データから、1枚で完結する HTML レポートを作る。

- JavaScript なし、CSS はインライン（外部ファイル不要）
- ユーザー由来の文字列は必ず html.escape する（XSS 対策）
- フッターに「どのコミットから作ったか」を表示する
  → GitHub Pages に公開されたページが、どのコミットのものか目で確認できる
"""

import datetime
import html
import os
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sales_report.aggregate import Sale, monthly_totals, top_products, total_revenue

_STYLE = """
:root {
  --bg: #faf6f1; --card: #ffffff; --text: #3b2f2a; --muted: #8a7a70;
  --accent: #b5651d; --bar-bg: #f0e6dc; --border: #e8ddd2;
}
@media (prefers-color-scheme: dark) {
  :root {
    --bg: #1d1815; --card: #2a2420; --text: #f1e8e0; --muted: #a8998e;
    --accent: #e0954f; --bar-bg: #3a322c; --border: #3f362f;
  }
}
* { box-sizing: border-box; }
body {
  margin: 0; background: var(--bg); color: var(--text); line-height: 1.6;
  font-family: "Hiragino Sans", "Yu Gothic", "Noto Sans JP", system-ui, sans-serif;
}
main { max-width: 760px; margin: 0 auto; padding: 24px 16px 8px; }
h1 { font-size: 1.5rem; margin: 0 0 4px; }
h2 { font-size: 1.1rem; margin: 0 0 12px; }
.period { margin: 0 0 20px; color: var(--muted); font-size: 0.9rem; }
.card {
  background: var(--card); border: 1px solid var(--border); border-radius: 12px;
  padding: 16px; margin-bottom: 16px;
}
.label { margin: 0; color: var(--muted); font-size: 0.85rem; }
.total { margin: 0; font-size: 2rem; font-weight: 700; color: var(--accent); }
table { width: 100%; border-collapse: collapse; }
th, td { padding: 8px 6px; border-bottom: 1px solid var(--border); text-align: left; }
th { color: var(--muted); font-size: 0.8rem; font-weight: 600; }
td.num, th.num { text-align: right; white-space: nowrap; font-variant-numeric: tabular-nums; }
.bar-cell { width: 45%; }
.bar-track { background: var(--bar-bg); border-radius: 4px; height: 14px; }
.bar { background: var(--accent); border-radius: 4px; height: 14px; }
.empty { color: var(--muted); }
footer {
  max-width: 760px; margin: 0 auto; padding: 8px 16px 32px;
  color: var(--muted); font-size: 0.8rem;
}
code { font-family: ui-monospace, SFMono-Regular, Menlo, monospace; }
@media (max-width: 480px) {
  .total { font-size: 1.6rem; }
  .bar-cell { width: 30%; }
}
"""


def _tokyo_tz() -> datetime.tzinfo:
    """日本時間のタイムゾーンを返す。

    Windows など tz データベースが無い環境では ZoneInfo が失敗するため、
    日本は夏時間が無い（常に UTC+9）ことを利用して固定オフセットで代用する。
    """
    try:
        return ZoneInfo("Asia/Tokyo")
    except ZoneInfoNotFoundError:
        return datetime.timezone(datetime.timedelta(hours=9), "JST")


def _format_yen(amount: int) -> str:
    """12345 -> '12,345円'"""
    return f"{amount:,}円"


def _commit_label() -> str:
    """ビルド元コミットの短縮表示。GitHub Actions 上では GITHUB_SHA の先頭7文字。"""
    sha = os.environ.get("GITHUB_SHA", "")
    return sha[:7] if sha else "local"


def _month_rows(sales: list[Sale]) -> str:
    """月別テーブルの行（CSS の横棒つき）。"""
    totals = monthly_totals(sales)
    if not totals:
        return '<tr><td colspan="3" class="empty">データがありません</td></tr>'
    max_total = max(totals.values())
    rows = []
    for month, amount in totals.items():
        # 最大の月を 100% とした相対幅。最大が 0 のときは割り算を避ける
        width = round(amount / max_total * 100, 1) if max_total else 0.0
        rows.append(
            "<tr>"
            f"<td>{html.escape(month)}</td>"
            '<td class="bar-cell"><div class="bar-track" aria-hidden="true">'
            f'<div class="bar" style="width: {width}%"></div></div></td>'
            f'<td class="num">{_format_yen(amount)}</td>'
            "</tr>"
        )
    return "\n".join(rows)


def _product_rows(sales: list[Sale]) -> str:
    """売れ筋トップ3テーブルの行。"""
    ranking = top_products(sales, 3)
    if not ranking:
        return '<tr><td colspan="3" class="empty">データがありません</td></tr>'
    return "\n".join(
        "<tr>"
        f'<td class="num">{rank}</td>'
        f"<td>{html.escape(name)}</td>"
        f'<td class="num">{_format_yen(amount)}</td>'
        "</tr>"
        for rank, (name, amount) in enumerate(ranking, start=1)
    )


def _period_text(sales: list[Sale]) -> str:
    if not sales:
        return ""
    first = min(sale.date for sale in sales)
    last = max(sale.date for sale in sales)
    return f'<p class="period">期間: {first.isoformat()} 〜 {last.isoformat()}</p>'


def render_html(
    sales: list[Sale],
    *,
    title: str = "売上レポート",
    generated_at: datetime.datetime | None = None,
) -> str:
    """売上リストから HTML 文字列を作る。

    generated_at はテストで時刻を固定するための引数。
    省略すると「いまの日本時間」を使う。
    """
    tz = _tokyo_tz()
    if generated_at is None:
        generated_at = datetime.datetime.now(tz)
    elif generated_at.tzinfo is None:
        # タイムゾーン無しで渡されたら日本時間とみなす
        generated_at = generated_at.replace(tzinfo=tz)
    else:
        generated_at = generated_at.astimezone(tz)
    stamp = generated_at.strftime("%Y-%m-%d %H:%M")

    safe_title = html.escape(title)
    return f"""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{safe_title}</title>
<style>{_STYLE}</style>
</head>
<body>
<main>
<h1>{safe_title}</h1>
{_period_text(sales)}
<section class="card">
<p class="label">総売上</p>
<p class="total">{_format_yen(total_revenue(sales))}</p>
</section>
<section class="card">
<h2>月別売上</h2>
<table>
<thead><tr><th>月</th><th></th><th class="num">売上</th></tr></thead>
<tbody>
{_month_rows(sales)}
</tbody>
</table>
</section>
<section class="card">
<h2>売れ筋トップ3</h2>
<table>
<thead><tr><th class="num">順位</th><th>商品</th><th class="num">売上</th></tr></thead>
<tbody>
{_product_rows(sales)}
</tbody>
</table>
</section>
</main>
<footer>
ビルド情報: commit <code>{html.escape(_commit_label())}</code> / 生成日時: {stamp} JST
</footer>
</body>
</html>
"""
