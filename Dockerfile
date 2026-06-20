# ==========================================
# 阶段一：使用 Node.js 镜像编译 Vue 3 静态前端
# ==========================================
FROM node:18-alpine AS frontend-builder
WORKDIR /app/frontend

# 拷贝前端依赖配置并安装依赖（设置淘宝/腾讯 NPM 镜像源加速）
COPY frontend/package.json ./
RUN npm install --registry=https://registry.npmmirror.com

# 拷贝前端所有源代码并进行生产编译
COPY frontend/ ./
RUN npm run build

# ==========================================
# 阶段二：使用 Python 镜像运行 FastAPI 后端并托管前端
# ==========================================
FROM python:3.11-slim AS runner
WORKDIR /app

# 设置环境变量，确保 Python 输出直接打印到控制台，且不生成 pyc 文件
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# 拷贝后端 Python 源码
COPY requirements.txt ./
COPY config.py database.py models.py crawler.py filter.py main.py scheduler.py server.py ./

# 安装后端依赖包（设置清华 pip 镜像源加速）
RUN pip install --no-cache-dir -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 从阶段一拷贝编译好的静态前端资源到跟 server.py 同级的 dist 目录
COPY --from=frontend-builder /app/frontend/dist ./dist

# 暴露端口，Render 部署时会自动传入环境变量 PORT
EXPOSE 8501

# 启动服务：使用 uvicorn 跑 FastAPI，支持 Render 传入的 PORT 环境变量
CMD ["sh", "-c", "uvicorn server:app --host 0.0.0.0 --port ${PORT:-8501}"]
