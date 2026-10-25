# cicd-handson

小さなカフェの売上CSVから HTML レポートを作るだけの、Python（標準ライブラリのみ）の小さなアプリです。
アプリそのものより、**GitHub に push して GitHub Actions を 1 ステップずつ有効にしていく**ための
学習用リポジトリです。ワークフローは `steps/` に置いてあり、`.github/workflows/` はあえて空にしてあります。
順番にコピーして、`git push` するたびに Actions タブで何が起きるかを確かめてください。

詳しい手順書（なぜそうするのか・画面の操作・つまずきやすい点）は、このリポジトリとは別の「ガイド」にあります。
ここには最低限の早見表だけを載せています。

## ディレクトリ構成

```
cicd-handson/
├── src/sales_report/        # アプリ本体（集計 aggregate.py / HTML生成 report.py / CLI cli.py）
├── tests/                   # pytest のテスト
├── data/sales.csv           # 架空の売上データ（2026-04〜2026-09）
├── steps/                   # ★ここからコピーして使うワークフロー
│   ├── 01-ci-minimal.yml
│   ├── 03-ci-full.yml
│   ├── 05-deploy-pages.yml
│   ├── 06-release-ghcr.yml
│   └── dependabot.yml
├── Dockerfile               # Step 6 で使う
├── pyproject.toml           # 依存・ruff・pytest・coverage の設定
└── README.md
```

## ステップ早見表

| Step | やること | コピーするファイル → コピー先 |
|------|----------|------------------------------|
| 1 | 最小の CI を動かす | `steps/01-ci-minimal.yml` → `.github/workflows/ci.yml` |
| 2 | わざとテストを壊して赤くする | （コピーなし。`aggregate.py` の `*` を `+` に変える） |
| 3 | Lint・複数バージョン・`ci-ok` を足す | `steps/03-ci-full.yml` → `.github/workflows/ci.yml`（上書き） |
| 4 | `ci-ok` を必須チェックにする | （コピーなし。GitHub の Settings 画面で設定） |
| 5 | GitHub Pages に自動公開 | `steps/05-deploy-pages.yml` → `.github/workflows/deploy.yml` |
| 6 | タグでイメージを GHCR に公開 | `steps/06-release-ghcr.yml` → `.github/workflows/release.yml` |
| 追加 | 依存の更新を自動で提案 | `steps/dependabot.yml` → `.github/dependabot.yml` |

## 手元ですぐ試す

```bash
python -m venv .venv
source .venv/bin/activate          # Windows(PowerShell): .venv\Scripts\Activate.ps1
pip install -e ".[dev]"

pytest                             # テスト
ruff check .                       # Lint
ruff format --check .              # 整形チェック（直すときは ruff format .）
python -m sales_report --input data/sales.csv --output site/index.html
```

`site/index.html` をブラウザで開くとレポートが見られます。
ページ下部の `commit local` は、GitHub Actions 上で作ると `commit 1a2b3c4`（コミットの先頭7文字）に変わります。

Python 3.12 以上が必要です。Docker を使う場合は `docker build -t sales-report .` のあと
`docker run --rm -v "$PWD/data:/data" sales-report` で `data/report.html` ができます。
