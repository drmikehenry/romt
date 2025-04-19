FROM ubuntu:20.04

RUN apt update \
  && DEBIAN_FRONTEND=noninteractive apt install -y \
      python3.9 \
      libpython3.9 \
      python3.9-venv \
      python3-pip \
  && rm -rf /var/lib/apt/lists/*

ARG ROMT_PIP_VERSION=25.0.1
ARG ROMT_PIPX_VERSION=1.7.1
ARG ROMT_POETRY_VERSION=2.1.2
ARG ROMT_POETRY_PLUGIN_EXPORT_VERSION=1.9.0

ENV PIPX_HOME=/pipx-lib
ENV PIPX_BIN_DIR=/usr/bin

RUN python3.9 -m venv /pipx-venv \
  && /pipx-venv/bin/pip install "pip==$ROMT_PIP_VERSION" \
  && /pipx-venv/bin/pip install "pipx==$ROMT_PIPX_VERSION" \
  && mkdir -p "$PIPX_HOME" \
  && /pipx-venv/bin/pipx install "pipx==$ROMT_PIPX_VERSION"

RUN pipx install "poetry==$ROMT_POETRY_VERSION" \
  && pipx inject poetry \
      "poetry-plugin-export==$ROMT_POETRY_PLUGIN_EXPORT_VERSION"

COPY --chmod=755 entrypoint.sh /entrypoint.sh

# Copy in project dependency specifications that don't change often; this
# speeds up incremental rebuilding of the container.
COPY pyproject.toml poetry.lock ./
RUN poetry install --no-root

COPY README.rst \
  maintainer.rst \
  noxfile.py \
  romt-wrapper.py \
  ./

ENTRYPOINT ["/entrypoint.sh"]
