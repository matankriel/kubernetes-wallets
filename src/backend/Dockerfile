FROM python:3.12-slim

# git is required by GitArgoProvisioner to commit changes to the helm-repo.
RUN apt-get update \
    && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy source before installing so that `pip install -e .` can find the package.
COPY pyproject.toml alembic.ini ./
COPY app/ ./app/
COPY alembic/ ./alembic/
COPY docker-entrypoint.sh /docker-entrypoint.sh

RUN pip install --no-cache-dir -e ".[dev]" \
    && chmod +x /docker-entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["/docker-entrypoint.sh"]
