FROM python:3.11-slim
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential gcc libssl-dev libffi-dev libpq-dev curl git && \
    rm -rf /var/lib/apt/lists/*
WORKDIR /workdir

COPY requirements.txt /workdir/requirements.txt
RUN python -m pip install --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt

COPY ./src /workdir
CMD ["python", "link_bot.py"]