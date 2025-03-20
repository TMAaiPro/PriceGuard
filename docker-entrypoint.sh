#!/bin/bash
# docker-entrypoint.sh

set -e

# Fonction pour attendre que PostgreSQL soit disponible
wait_for_postgres() {
    echo "Waiting for PostgreSQL..."
    while ! nc -z ${DATABASE_HOST:-db} ${DATABASE_PORT:-5432}; do
        sleep 0.1
    done
    echo "PostgreSQL started"
}

# Fonction pour attendre que Redis soit disponible
wait_for_redis() {
    echo "Waiting for Redis..."
    while ! nc -z ${REDIS_HOST:-redis} ${REDIS_PORT:-6379}; do
        sleep 0.1
    done
    echo "Redis started"
}

# Attendre les services dépendants
wait_for_postgres
wait_for_redis

# Appliquer les migrations
if [ "$1" = "web" ] || [ "$1" = "migrate" ]; then
    echo "Applying database migrations..."
    python manage.py migrate --noinput
fi

# Collecter les fichiers statiques
if [ "$1" = "web" ]; then
    echo "Collecting static files..."
    python manage.py collectstatic --noinput
fi

# Exécuter la commande spécifiée
case "$1" in
    web)
        echo "Starting Django web server..."
        gunicorn priceguard.wsgi:application --bind 0.0.0.0:8000 --workers 4 --timeout 120
        ;;
    worker)
        echo "Starting Celery worker..."
        celery -A priceguard worker --loglevel=info --concurrency=8
        ;;
    beat)
        echo "Starting Celery beat..."
        celery -A priceguard beat --loglevel=info
        ;;
    flower)
        echo "Starting Flower monitoring..."
        celery -A priceguard flower --port=5555 --address=0.0.0.0
        ;;
    migrate)
        echo "Migrations completed."
        ;;
    shell)
        python manage.py shell
        ;;
    *)
        exec "$@"
        ;;
esac
