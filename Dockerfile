# 使用基础镜像，这里以Python官方镜像为例
FROM python:3.9-slim

WORKDIR /app

COPY ./media-subscribe /app/media-subscribe
COPY ./requirements.txt /app

RUN apt-get update && \
    apt-get install -y ffmpeg && \
    rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 8000

VOLUME ["/app/db", "/app/config", "/app/logs", "/app/downloads"]

CMD ["python", "media-subscribe/main.py"]

