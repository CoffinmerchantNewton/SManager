FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY app ./app
COPY run.py .
COPY docker-entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

RUN mkdir -p runtime/fnl runtime/products runtime/logs runtime/manifests runtime/cache

EXPOSE 8000

ENTRYPOINT ["/entrypoint.sh"]
