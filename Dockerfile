FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
ENV PORT=8000
EXPOSE 8000
CMD ["sh", "-c", "python -m uvicorn server.app:create_app --factory --host 0.0.0.0 --port ${PORT:-8000}"]
