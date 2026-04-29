FROM python:3.11-slim
WORKDIR /app
COPY pyproject.toml README.md ./
COPY edalauncher ./edalauncher
RUN pip install --no-cache-dir -e . && \
    useradd -m -u 1001 eda
USER eda
EXPOSE 5000
ENTRYPOINT ["edalauncher", "serve", "--host", "0.0.0.0"]
