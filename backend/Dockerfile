# Используем стабильный Debian bookworm, чтобы избежать проблем apt у trixie
FROM python:3.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Сначала ставим зависимости — кэшируется
COPY requirements.txt ./
RUN python -m pip install --upgrade pip setuptools wheel \
 && pip install -r requirements.txt

# Затем копируем весь проект
COPY . .

EXPOSE 8000

# Запуск по умолчанию (может быть переопределён в docker-compose)
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "foodgram.wsgi"]
