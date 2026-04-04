#!/bin/sh
set -e

echo "применяю миграции..."
alembic upgrade head

echo "запускаю приложение..."
exec "$@"