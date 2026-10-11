# Imagen de la app (plan 0000 §9). Python 3.12, como fija la constitución (art. 7.1).
FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY pyproject.toml ./
COPY src ./src
RUN pip install --no-cache-dir -e . gunicorn==23.0.0
COPY . .
EXPOSE 8000
CMD ["sh", "-c", "python manage.py migrate --noinput && gunicorn config.wsgi --bind 0.0.0.0:8000 --workers 3"]
