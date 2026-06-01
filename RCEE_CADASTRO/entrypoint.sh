#!/bin/bash
set -e

echo "Aguardando MySQL..."
while ! python -c "
import pymysql, os, sys
host = os.environ.get('DB_HOST', 'mysql')
user = os.environ.get('DB_USER', 'rcee_user')
password = os.environ.get('DB_PASSWORD', 'rcee123')
database = os.environ.get('DB_NAME', 'rcee_cadastro_db')
try:
    pymysql.connect(host=host, user=user, password=password, database=database, connect_timeout=5)
    sys.exit(0)
except Exception as e:
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
import os
import pymysql
from werkzeug.security import generate_password_hash

host = os.environ.get("DB_HOST", "mysql")
user = os.environ.get("DB_USER", "rcee_user")
pw = os.environ.get("DB_PASSWORD", "rcee123")
db_name = os.environ.get("DB_NAME", "rcee_cadastro_db")

# Dados do Admin
admin_email = "admin@rcee.local"
admin_pass = "Admin@123"
admin_name = "Administrador Sistema"

conn = pymysql.connect(host=host, user=user, password=pw, database=db_name, autocommit=True)

try:
    with conn.cursor() as cur:
        # Verifica se já existe
        cur.execute("SELECT id FROM user WHERE email = %s", (admin_email,))
        if not cur.fetchone():
            hash_pw = generate_password_hash(admin_pass)
            sql = "INSERT INTO user (name, email, password_hash, role, is_active, created_at, instituicao) VALUES (%s, %s, %s, %s, %s, NOW(), %s)"
            cur.execute(sql, (admin_name, admin_email, hash_pw, "Admin", 1, "RCEE"))
            print(f"Sucesso: Usuário {admin_email} criado.")
        else:
            print(f"Info: Usuário {admin_email} já existe.")
finally:
    conn.close()
PY

echo "Iniciando aplicação..."
exec "$@"