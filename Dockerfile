# Dockerfile
FROM python:3.10-slim

ENV DEBIAN_FRONTEND=noninteractive
WORKDIR /app

# 更新并安装系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    wget \
    curl \
    ffmpeg \
    libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

# 复制项目文件并安装依赖
COPY pyproject.toml README.md /app/
COPY src/ /app/src/
RUN pip install --upgrade pip setuptools wheel && \
    pip install -e /app/

# 复制应用文件
COPY server.py /app/
COPY templates/ /app/templates/
COPY hotwords.txt /app/

# 创建临时目录和输出目录
RUN mkdir -p /app/temp_dir /app/output_dir && chmod 777 /app/temp_dir /app/output_dir

# 暴露端口
EXPOSE 8001

# 使用exec形式启动，确保信号正确传递
ENTRYPOINT ["python", "server.py"]
CMD ["--host", "0.0.0.0", "--port", "8001"]