# Используем официальный Python образ
FROM python:3.10-slim

# Устанавливаем рабочую директорию
WORKDIR /app

# Устанавливаем зависимости системы (например, для lxml потребуется libxml2 и libxslt)
RUN apt-get update && apt-get install -y --no-install-recommends \
        libpq-dev gcc build-essential libxml2-dev libxslt1-dev && \
    rm -rf /var/lib/apt/lists/*

# Копируем файлы с зависимостями
COPY requirements.txt /app/
# Устанавливаем зависимости
RUN pip install --no-cache-dir --trusted-host pypi.org --trusted-host pypi.python.org --trusted-host files.pythonhosted.org -r requirements.txt

# Копируем все файлы проекта в контейнер
COPY . /app/

# Открываем порт 8000 для Django (опционально, для внешнего доступа)
EXPOSE 8000

# Команда запуска по умолчанию (может быть переопределена в docker-compose)
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
