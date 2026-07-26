FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN groupadd -r django && useradd -r -g django django
USER django

EXPOSE 8000

CMD ["gunicorn", "meal_planner_service.wsgi:application", \
     "--bind", "0.0.0.0:8000", \
     "--workers", "1", "--threads", "4", "--timeout", "190", \
     "--access-logfile", "-", "--error-logfile", "-"]
