#!/bin/bash
set -e

echo "Aguardando MySQL..."
while ! python -c "
import pymysql, os, sys
host = os.environ.get('DB_HOST', 'mysql')
user = os.environ.get('DB_USER', 'rcee_user')
password = os.environ.get('DB_PASSWORD', 'rcee123')
database = os.environ.get('DB_NAME', 'rcee_admin_db')
try:
    pymysql.connect(host=host, user=user, password=password, database=database, connect_timeout=5)
    sys.exit(0)
except:
    sys.exit(1)
"; do
    echo "MySQL não está pronto, aguardando 2s..."
    sleep 2
done

echo "MySQL pronto! Criando tabelas..."
python -c "
from app import create_app, db
app = create_app()
with app.app_context():
    db.create_all()
    print('Tabelas sincronizadas.')
"

echo "Garantindo usuário administrador padrão..."
python - <<'PY'
import os, pymysql
from werkzeug.security import generate_password_hash

conn = pymysql.connect(
    host=os.environ.get("DB_HOST", "mysql"),
    user=os.environ.get("DB_USER", "rcee_user"),
    password=os.environ.get("DB_PASSWORD", "rcee123"),
    database=os.environ.get("DB_NAME", "rcee_admin_db"),
    autocommit=True
)
try:
    with conn.cursor() as cur:
        cur.execute("SELECT id FROM user WHERE email = %s", ("admin@rcee.local",))
        if not cur.fetchone():
            cur.execute(
                "INSERT INTO user (name, email, password_hash, role, is_active, created_at, instituicao) VALUES (%s, %s, %s, %s, %s, NOW(), %s)",
                ("Administrador Sistema", "admin@rcee.local", generate_password_hash("Admin@123"), "Admin", 1, "RCEE")
            )
            print("Usuário admin criado em rcee_admin_db.")
        else:
            print("Usuário admin já existe em rcee_admin_db.")
finally:
    conn.close()
PY

echo "Iniciando aplicação..."
exec "$@"