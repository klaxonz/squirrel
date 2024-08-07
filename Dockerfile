# 使用基础镜像，这里以Python官方镜像为例
FROM python:3.11-slim

WORKDIR /app

# 安装必要的依赖
RUN apt-get update && \
    apt-get install -y \
    wget \
    xz-utils \
    build-essential \
    nasm \
    && rm -rf /var/lib/apt/lists/*

# 下载并安装FFmpeg 6.0
RUN wget https://ffmpeg.org/releases/ffmpeg-6.0.tar.xz \
    && tar -xJf ffmpeg-6.0.tar.xz \
    && cd ffmpeg-6.0 \
    && ./configure --disable-static --enable-shared \
    && make \
    && make install \
    && cd .. \
    && rm -rf ffmpeg-6.0 ffmpeg-6.0.tar.xz

# 更新动态链接库
RUN ldconfig

# 安装pipenv
RUN pip install --no-cache-dir pipenv

# 第二阶段：安装依赖并运行应用
COPY Pipfile Pipfile.lock /app/
COPY ./media-subscribe /app/media-subscribe
RUN pipenv install --deploy

EXPOSE 8000

CMD ["pipenv", "run", "python", "media-subscribe/main.py"]