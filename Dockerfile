# =============================================================================
# Dockerfile : sales-report を「どこでも同じように動く箱(コンテナイメージ)」にする
# -----------------------------------------------------------------------------
# ビルド : docker build -t sales-report .
# 実行   : docker run --rm -v "$PWD/data:/data" sales-report
#            → ./data/sales.csv を読んで ./data/report.html を作る
#
# 補足(Linux のホストで実行する場合):
#   コンテナ内のユーザー(UID 10001)にホスト側フォルダの書き込み権限が無いと、
#   report.html を作れず Permission denied になる。その場合は
#   docker run --rm --user "$(id -u):$(id -g)" -v "$PWD/data:/data" sales-report
#   のように、自分の UID で実行する。(Docker Desktop の Windows/Mac では通常不要)
#
# Step 6 では、この Dockerfile を GitHub Actions が自動でビルドして GHCR に push する。
# =============================================================================

# ベースイメージ。slim は余計なものを省いた軽量版。
# CI の matrix(3.13 / 3.14 / 3.15)の真ん中のバージョンに合わせている。
FROM python:3.14-slim

# ソースリポジトリとの紐づけ(OCI 標準ラベル)について:
#   LABEL org.opencontainers.image.source="https://github.com/<ユーザー名>/<リポジトリ名>"
#   と書くと、GHCR のパッケージがそのリポジトリに紐づく。
#   ただし Step 6 では docker/metadata-action が同じラベルを自動で付けるため、
#   ここには書かなくてよい（手動で docker build / push する場合に書く）。

# PYTHONDONTWRITEBYTECODE : .pyc を作らない（コンテナ内では不要で、書き込み権限の問題も避けられる）
# PYTHONUNBUFFERED        : print の出力をすぐにログへ流す
# PIP_DISABLE_PIP_VERSION_CHECK / PIP_ROOT_USER_ACTION : ビルドログのノイズ(警告)を減らす
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_ROOT_USER_ACTION=ignore

# root で動かさないための一般ユーザーを作る（セキュリティの基本）。
# /data は入出力用フォルダ。このユーザーが書き込めるようにしておく。
RUN useradd --create-home --uid 10001 app \
    && mkdir /data \
    && chown app:app /data

WORKDIR /app

# アプリのインストールに必要なファイルだけをコピーする。
# (tests/ や steps/ などは入れない → イメージが小さくなり、ビルドキャッシュも効きやすい)
COPY pyproject.toml ./
COPY src ./src

# --no-cache-dir : pip のダウンロードキャッシュを残さない（イメージを小さくする）
RUN pip install --no-cache-dir .

# ここから先は一般ユーザー(上で作った UID 10001)で実行する。
# 名前(app)ではなく数字で指定するのは、Kubernetes などが「root ではない」ことを
# 数字の UID で確認できるようにするため（hadolint の DL3066 の指摘）。
USER 10001

# ENTRYPOINT : 常に実行されるコマンド本体。
# CMD        : 既定の引数。docker run の末尾で上書きできる。
#   例) docker run --rm -v "$PWD/data:/data" sales-report --input /data/other.csv --output /data/other.html
ENTRYPOINT ["python", "-m", "sales_report"]
CMD ["--input", "/data/sales.csv", "--output", "/data/report.html"]
