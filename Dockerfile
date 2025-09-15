FROM debian:trixie

COPY --from=ghcr.io/astral-sh/uv:0.8 /uv /uvx /bin/
COPY ./uv.lock ./pyproject.toml /

RUN echo 'debconf debconf/frontend select Noninteractive' | debconf-set-selections
RUN apt-get -q update
RUN apt-get -y upgrade
RUN apt-get -y install python3-dev build-essential libmariadb-dev
RUN uv sync --locked
COPY stats.py /
