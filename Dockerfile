# stage 1: build
FROM python:3.11-bullseye as builder

# install packages needed by python packages
RUN apt-get update \
    && apt-get install -y build-essential \
    && rm -rf /var/lib/apt/lists/*

# create virtualenv and install dependencies
RUN python -m venv /app/venv
ENV PATH="/app/venv/bin:$PATH"
COPY requirements.txt .
RUN pip install -r requirements.txt

# stage 2: runtime
FROM python:3.11-slim-bullseye

# install packages needed needed at runtime
RUN apt-get update \
    && apt-get install -y --no-install-recommends git openssh-client procps libpq5 \
    && apt-get purge -y --auto-remove \
    && rm -rf /var/lib/apt/lists/*

# create user
RUN addgroup --system app && adduser --system --group app
USER app
WORKDIR /app

# copy virtualenv from builder
COPY --chown=app:app --from=builder /app/venv /app/venv
# copy application code. update .dockerignore to files that shouldn't be copied
COPY --chown=app:app . .

ENV PATH="/app/venv/bin:$PATH"
CMD  ["/bin/sh", "/app/entrypoint.sh"]

EXPOSE 8000
