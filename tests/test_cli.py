"""cli.py（コマンドライン）のテスト。"""

import re
import runpy
import sys
from pathlib import Path

import pytest

import sales_report
from sales_report.cli import main


def test_version_looks_like_semver() -> None:
    assert re.fullmatch(r"\d+\.\d+\.\d+", sales_report.__version__)


def test_main_writes_html_and_returns_zero(
    sample_csv: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    out = tmp_path / "site" / "index.html"  # site/ はまだ存在しない
    code = main(["--input", str(sample_csv), "--output", str(out)])

    assert code == 0
    assert out.exists()
    assert "11,400円" in out.read_text(encoding="utf-8")
    assert capsys.readouterr().out.strip() == str(out)  # 出力パスを表示する


def test_main_creates_nested_parent_directories(sample_csv: Path, tmp_path: Path) -> None:
    out = tmp_path / "a" / "b" / "c" / "report.html"
    assert main(["--input", str(sample_csv), "--output", str(out)]) == 0
    assert out.exists()


def test_main_returns_one_for_bad_csv(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    bad = tmp_path / "bad.csv"
    bad.write_text("date,product,quantity,unit_price\n2026-04-01,紅茶,abc,800\n", encoding="utf-8")
    out = tmp_path / "site" / "index.html"

    code = main(["--input", str(bad), "--output", str(out)])

    assert code == 1
    assert not out.exists()  # 失敗したら HTML は作らない
    err = capsys.readouterr().err
    assert "エラー" in err
    assert "2行目" in err


def test_main_returns_one_when_input_file_is_missing(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    code = main(["--input", str(tmp_path / "nothing.csv"), "--output", str(tmp_path / "o.html")])
    assert code == 1
    assert "エラー" in capsys.readouterr().err


def test_python_dash_m_entry_point(
    sample_csv: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`python -m sales_report` 相当（__main__.py）が動く。"""
    out = tmp_path / "index.html"
    monkeypatch.setattr(
        sys, "argv", ["sales_report", "--input", str(sample_csv), "--output", str(out)]
    )
    with pytest.raises(SystemExit) as excinfo:
        runpy.run_module("sales_report", run_name="__main__")
    assert excinfo.value.code == 0
    assert out.exists()
