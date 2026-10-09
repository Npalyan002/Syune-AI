FROM python:3.12.10-slim-bookworm@sha256:fd95fa221297a88e1cf49c55ec1828edd7c5a428187e67b5d1805692d11588db

ARG UV_VERSION=0.12.24
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PATH=/opt/syune/.venv/bin:$PATH

RUN groupadd --system --gid 10001 syune \
    && useradd --system --uid 10001 --gid syune --home /nonexistent --shell /usr/sbin/nologin syune \
    && python -m pip install --no-cache-dir "uv==${UV_VERSION}"

WORKDIR /opt/syune
COPY pyproject.toml uv.lock README.md LICENSE ./
COPY src ./src
RUN uv sync --frozen --no-dev --no-editable \
    && mkdir -p /var/lib/syune-aml \
    && chown -R syune:syune /var/lib/syune-aml

USER 10001:10001
EXPOSE 8080
STOPSIGNAL SIGTERM
CMD ["uvicorn", "syune.adapters.aml.v1:app_from_environment", "--factory", "--host", "0.0.0.0", "--port", "8080", "--workers", "1", "--limit-concurrency", "8", "--timeout-keep-alive", "5", "--timeout-graceful-shutdown", "1800", "--no-access-log", "--no-server-header"]
