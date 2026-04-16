FROM python:3.11-slim
WORKDIR /app
RUN pip install --no-cache-dir aiogram==3.15.0
COPY bot.py .
CMD ["python", "bot.py"]
