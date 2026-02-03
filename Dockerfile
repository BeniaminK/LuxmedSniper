FROM ghcr.io/astral-sh/uv:python3.14-alpine

# Copy the project into the image
COPY pyproject.toml uv.lock /app/
# Disable development dependencies
ENV UV_NO_DEV=0
# Enable bytecode compilation
ENV UV_COMPILE_BYTECODE=1

# Sync the project into a new environment, asserting the lockfile is up to date
WORKDIR /app
# Install dependencies using the lockfile (only telegram extra)
RUN uv sync --frozen --no-install-project --no-dev --extra telegram

COPY . /app

# Run the application using uv run, which will use the environment created by uv sync
ENTRYPOINT ["uv", "run", "luxmed_sniper.py"]
CMD ["-d", "300"]
