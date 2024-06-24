# 使用基础镜像，这里以Python官方镜像为例
FROM python:3.11-slim

WORKDIR /app

# 安装FFmpeg
RUN apt-get update && \
    apt-get install -y ffmpeg && \
    rm -rf /var/lib/apt/lists/*

# 安装pipenv
RUN pip install --no-cache-dir pipenv

# 第二阶段：安装依赖并运行应用
COPY Pipfile Pipfile.lock /app/
COPY ./media-subscribe /app/media-subscribe
RUN pipenv install --deploy

EXPOSE 8000

CMD ["pipenv", "run", "python", "media-subscribe/main.py"]
