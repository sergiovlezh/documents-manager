FROM python:3.13.11-slim-trixie

ENV DEBIAN_FRONTEND=noninteractive

# Install base dependencies
RUN apt update && apt install -y \
    git \
    openssh-client \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv
RUN curl -LsSf https://astral.sh/uv/install.sh | sh

# Workspace
RUN mkdir -p /workspaces
WORKDIR /workspaces
