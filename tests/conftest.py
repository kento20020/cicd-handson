"""テスト共通の準備（フィクスチャ）。

data/sales.csv には依存せず、テスト専用の小さな CSV をその場で作ります。
金額を手計算しやすいよう、数字はキリのいい値にしてあります。

    2026-04: 2*1500 + 1*800  = 3800
    2026-05: 1*1500 + 3*300 + 1*2000 = 4400
    2026-06: 4*800 = 3200
    合計 11400
    商品別: コーヒー豆 4500 / 紅茶 4000 / マグカップ 2000 / クッキー 900
"""

from pathlib import Path

import pytest

SAMPLE_CSV = """date,product,quantity,unit_price
2026-04-01,コーヒー豆,2,1500
2026-04-15,紅茶,1,800
2026-05-03,コーヒー豆,1,1500
2026-05-20,クッキー,3,300
2026-05-21,マグカップ,1,2000
2026-06-10,紅茶,4,800
"""


@pytest.fixture
def sample_csv(tmp_path: Path) -> Path:
    """テスト用の小さな売上 CSV を一時フォルダに書き出して、そのパスを返す。"""
    path = tmp_path / "sales.csv"
    path.write_text(SAMPLE_CSV, encoding="utf-8")
    return path
