# Python和uv来自官方镜像；具体Python依赖继续由uv.lock固定。
FROM python:3.12-slim-bookworm
COPY --from=ghcr.io/astral-sh/uv:0.11.1 /uv /usr/local/bin/uv

WORKDIR /app
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUTF8=1 \
    UV_PYTHON_DOWNLOADS=never \
    UV_LINK_MODE=copy \
    PATH="/app/.venv/bin:$PATH"

# 先安装锁定依赖；只改Python代码时，可以复用这一层。
COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-dev --no-install-project --no-cache --python /usr/local/bin/python

COPY lesson*.py ./
RUN groupadd --gid 10001 agent \
    && useradd --uid 10001 --gid agent --create-home agent \
    && mkdir -p /app/data/chunks /app/data/vectors /app/skills
USER 10001:10001

EXPOSE 8000
# 监听容器网卡，宿主机的开放范围由Compose端口映射决定。
CMD ["python", "-m", "uvicorn", "lesson10a:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
