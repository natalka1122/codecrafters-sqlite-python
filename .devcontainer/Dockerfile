FROM mcr.microsoft.com/devcontainers/base:ubuntu-24.04

# Install packages
RUN apt-get update && \
    apt-get install -y software-properties-common && \
    add-apt-repository ppa:deadsnakes/ppa && \
    apt update && \
    apt install -y python3.14 python3-pip python3-venv git python-is-python3 iputils-ping net-tools telnet tcpdump redis-tools netcat-openbsd dnsutils && \
    apt clean && \
    rm -rf /var/lib/apt/lists/*

RUN update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.14 1

RUN pip install --break-system-packages --upgrade argcomplete mypy pytest pytest-cov pytest-asyncio black wemake-python-styleguide cohesion dlint pytest-xdist vulture isort jupyter pipenv uv flake8

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen

# Install Codecrafters Python
RUN curl https://codecrafters.io/install.sh | sh
