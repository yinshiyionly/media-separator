# 使用最小化的 Python 基础镜像
FROM python:3.9-alpine

# 设置工作目录
WORKDIR /app

# 复制 Python 脚本到容器内
COPY app.py /app/

COPY .env /app/

# 安装运行服务器所需的基础依赖
RUN apk add --no-cache \
    build-base \
    libffi-dev \
    && pip install --no-cache-dir --upgrade pip dotenv  \
    && apk del build-base libffi-dev

# 设置监听端口
EXPOSE 6002

# 运行 Python 脚本
CMD ["python", "/app/app.py"]
