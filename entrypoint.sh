#!/bin/bash

# Attendre que la base de données soit prête
if [ "$DATABASE_URL" != "" ]; then
    echo "Waiting for postgres..."

    while ! nc -z $DB_HOST $DB_PORT; do
      sleep 0.1
    done

    echo "PostgreSQL started"
fi

# Appliquer les migrations de base de données
python manage.py migrate

# Créer un super utilisateur si nécessaire
if [ "$DJANGO_SUPERUSER_USERNAME" ] && [ "$DJANGO_SUPERUSER_PASSWORD" ] && [ "$DJANGO_SUPERUSER_EMAIL" ]; then
    python manage.py createsuperuser \
        --noinput \
        --username "$DJANGO_SUPERUSER_USERNAME" \
        --email "$DJANGO_SUPERUSER_EMAIL"
fi

# Collecter les fichiers statiques
python manage.py collectstatic --no-input

# Lancer Gunicorn
exec gunicorn priceguard.wsgi:application \
    --bind 0.0.0.0:8000 \
    --workers 3 \
    --worker-tmp-dir /dev/shm \
    --log-level=info \
    --access-logfile=- \
    --error-logfile=-