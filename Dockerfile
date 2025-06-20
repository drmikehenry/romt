FROM ubuntu:14.04

RUN apt update \
  && apt install -y \
      binutils \
      curl \
  && rm -rf /var/lib/apt/lists/*

ARG ROMT_UV_VERSION="0.7.19"
ARG ROMT_UV_PYTHON_VERSION="3.13"
ARG ROMT_UV_PACKAGE="uv-x86_64-unknown-linux-musl.tar.gz"
ARG ROMT_UV_DOWNLOAD_BASE="https://github.com/astral-sh/uv/releases/download"
ARG ROMT_UV_URL="$ROMT_UV_DOWNLOAD_BASE/$ROMT_UV_VERSION/$ROMT_UV_PACKAGE"

RUN curl -L "$ROMT_UV_URL" -o "/tmp/$ROMT_UV_PACKAGE" \
  && tar -C /tmp -xf "/tmp/$ROMT_UV_PACKAGE" \
  && cp /tmp/uv-*/uv* /usr/local/bin \
  && rm -rf /tmp/uv*

RUN uv python install "$ROMT_UV_PYTHON_VERSION"

# Copy in project dependency specifications that don't change often; this
# speeds up incremental rebuilding of the container.
COPY pyproject.toml uv.lock ./
RUN uv sync --no-install-package romt

COPY README.rst \
  maintainer.rst \
  noxfile.py \
  romt-wrapper.py \
  ./
COPY src ./src

RUN uv run nox -s build \
  && cp dist/x86_64-linux/* /usr/local/bin

ENTRYPOINT ["romt", "--version"]
