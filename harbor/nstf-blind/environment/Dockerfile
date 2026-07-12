FROM python:3.13-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    bash ca-certificates curl git jq nodejs npm procps ripgrep \
    && rm -rf /var/lib/apt/lists/*

# Science stack for the agent; pydantic for the vendored verifier scorer.
RUN pip install --no-cache-dir \
    "numpy>=2" "scipy>=1.14" "pandas>=2.2" "matplotlib>=3.9" "CoolProp>=6.6" \
    "pydantic>=2.12,<3"

COPY pack/ /app/
RUN mkdir -p /app/output

WORKDIR /app
