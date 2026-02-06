# Reference: https://docs.astral.sh/uv/guides/integration/docker/#installing-uv

FROM python:3.13-slim

RUN apt-get update && apt-get install -y --no-install-recommends curl ca-certificates \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

ADD https://astral.sh/uv/install.sh /uv-installer.sh
RUN sh /uv-installer.sh && rm /uv-installer.sh
RUN mv /root/.local/bin/uv /usr/local/bin/uv

RUN groupadd -r icedtea && useradd -r -g icedtea -m icedtea

WORKDIR /app
RUN chown icedtea:icedtea /app
USER icedtea

COPY --chown=icedtea:icedtea pyproject.toml uv.lock ./
COPY --chown=icedtea:icedtea README.md ./
COPY --chown=icedtea:icedtea ctfeed.py ./
COPY --chown=icedtea:icedtea src/ ./src/

RUN uv sync --frozen

CMD ["/bin/bash", "./startup.sh"]