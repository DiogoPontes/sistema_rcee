#!/usr/bin/env python3
"""
Consumidor Kafka -> rcee_admin (Preparado para máquinas separadas via HTTP)
"""

import os
import json
import signal
import logging
import requests
from time import sleep
from datetime import datetime
from confluent_kafka import Consumer, KafkaException
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from dotenv import load_dotenv

# Carrega .env.consumer
here = os.path.dirname(os.path.abspath(__file__))
env_path = os.path.join(here, ".env.consumer")
load_dotenv(env_path)

# Configurações
KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:29092")
KAFKA_TOPICS = os.getenv("KAFKA_TOPIC", "post_published").split(",")
KAFKA_GROUP_ID = os.getenv("KAFKA_GROUP_ID", "sync-rcee-admin")
DB_URL = os.getenv("DATABASE_URL")

# Configurações de Assets (HTTP)
ASSETS_ENABLED = os.getenv("ASSETS_ENABLED", "true").lower() in ("1", "true", "yes")
UPLOADS_CADASTRO_BASE_URL = os.getenv("UPLOADS_CADASTRO_BASE_URL", "http://localhost:5000")
ADMIN_UPLOADS_PATH = os.getenv("ADMIN_UPLOADS_PATH", "C:/xampp/htdocs/RCEE_ADMIN/app/static/uploads")
MAX_ASSET_RETRIES = int(os.getenv("MAX_ASSET_RETRIES", "3"))
ASSET_DOWNLOAD_TIMEOUT = int(os.getenv("ASSET_DOWNLOAD_TIMEOUT", "30"))
FAIL_ON_ASSET_ERROR = os.getenv("FAIL_ON_ASSET_ERROR", "false").lower() in ("1", "true", "yes")

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s:%(name)s:%(message)s")
logger = logging.getLogger("sync-rcee-admin")

KAFKA_CONFIG = {
    "bootstrap.servers": KAFKA_BOOTSTRAP_SERVERS,
    "group.id": KAFKA_GROUP_ID,
    "auto.offset.reset": "earliest",
    "enable.auto.commit": False,
}

SHUTDOWN = False

def handle_sigterm(signum, frame):
    global SHUTDOWN
    SHUTDOWN = True

signal.signal(signal.SIGINT, handle_sigterm)
signal.signal(signal.SIGTERM, handle_sigterm)


def parse_iso_datetime(s):
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.rstrip("Z"))
    except Exception:
        return None


UPSERT_SQL = text("""
INSERT INTO post (id, title, slug, summary, body, featured_image, status, category_id, author_id, published_at, created_at, updated_at)
VALUES (:id, :title, :slug, :summary, :body, :featured_image, :status, :category_id, :author_id, :published_at, :created_at, :updated_at)
ON DUPLICATE KEY UPDATE
  title=VALUES(title), slug=VALUES(slug), summary=VALUES(summary), body=VALUES(body), featured_image=VALUES(featured_image),
  status=VALUES(status), category_id=VALUES(category_id), author_id=VALUES(author_id), published_at=VALUES(published_at), updated_at=VALUES(updated_at)
""")

DELETE_ASSETS_SQL = text("DELETE FROM post_asset WHERE post_id = :post_id")

INSERT_ASSET_SQL = text("""
INSERT INTO post_asset (post_id, asset_type, title, url, file_path)
VALUES (:post_id, :asset_type, :title, :url, :file_path)
""")


def download_asset(filename: str) -> str:
    """
    Baixa o arquivo via HTTP da origem (Cadastro) e salva no destino (Admin).
    """
    clean_filename = filename.replace("\\", "/").lstrip("/")
    if clean_filename.startswith("static/uploads/"):
        clean_filename = clean_filename[len("static/uploads/"):]

    base_url = UPLOADS_CADASTRO_BASE_URL.rstrip("/")
    if "/static/uploads" not in base_url:
        url = f"{base_url}/static/uploads/{clean_filename}"
    else:
        url = f"{base_url}/{clean_filename}"

    dest_path = os.path.normpath(os.path.join(ADMIN_UPLOADS_PATH, clean_filename))
    os.makedirs(os.path.dirname(dest_path), exist_ok=True)

    attempt = 0
    while attempt < MAX_ASSET_RETRIES:
        attempt += 1
        try:
            logger.info(f"Tentativa {attempt}: Baixando {url} -> {dest_path}")
            resp = requests.get(url, stream=True, timeout=ASSET_DOWNLOAD_TIMEOUT)
            resp.raise_for_status()

            with open(dest_path, "wb") as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)

            logger.info("Download concluído com sucesso.")
            return dest_path
        except Exception as e:
            logger.error(f"Erro no download (tentativa {attempt}): {e}")
            if attempt < MAX_ASSET_RETRIES:
                sleep(2)
            else:
                raise


def process_message(engine: Engine, msg_value: bytes):
    """
    Processa mensagens do tópico post_published - faz upsert no DB e baixa assets.
    """
    payload = json.loads(msg_value.decode("utf-8"))
    post_id = payload.get("id")

    data = {
        "id": payload.get("id"),
        "title": payload.get("title"),
        "slug": payload.get("slug"),
        "summary": payload.get("summary"),
        "body": payload.get("body"),
        "featured_image": payload.get("featured_image"),
        "status": payload.get("status"),
        "category_id": payload.get("category_id"),
        "author_id": payload.get("author_id"),
        "published_at": parse_iso_datetime(payload.get("published_at")),
        "created_at": parse_iso_datetime(payload.get("created_at")),
        "updated_at": parse_iso_datetime(payload.get("updated_at")),
    }

    with engine.begin() as conn:
        conn.execute(UPSERT_SQL, data)
        logger.info("Upsert concluído para post id=%s", data.get("id"))

        assets_payload = payload.get("assets", [])
        conn.execute(DELETE_ASSETS_SQL, {"post_id": post_id})

        for asset_data in assets_payload:
            asset_row = {
                "post_id": post_id,
                "asset_type": asset_data.get("asset_type"),
                "title": asset_data.get("title"),
                "url": asset_data.get("url"),
                "file_path": asset_data.get("file_path")
            }
            conn.execute(INSERT_ASSET_SQL, asset_row)

            if ASSETS_ENABLED and asset_row["file_path"]:
                try:
                    download_asset(asset_row["file_path"])
                except Exception as e:
                    logger.warning(f"Falha ao baixar anexo {asset_row['file_path']}: {e}")

    if ASSETS_ENABLED and data.get("featured_image"):
        try:
            download_asset(data["featured_image"])
        except Exception as e:
            logger.warning(f"Falha ao sincronizar imagem para post {data.get('id')}: {e}")
            if FAIL_ON_ASSET_ERROR:
                raise


# ---------------------------------------------------------------------------
# Funções para processar mensagens do tópico post_status_update_admin
# ---------------------------------------------------------------------------

def atualizar_status_cadastro(post_id, status) -> bool:
    """Atualiza apenas o status do post no CADASTRO via PATCH /posts/<id>/status"""
    cadastro_api_url = os.getenv("CADASTRO_API_URL", "http://rcee-cadastro:5000")
    cadastro_api_token = os.getenv("CADASTRO_API_TOKEN", "seu_token_aqui")

    url = f"{cadastro_api_url.rstrip('/')}/posts/{post_id}/status"
    headers = {
        "Authorization": f"Bearer {cadastro_api_token}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    payload = {"status": status}

    try:
        logger.info("Atualizando status do post %s para %s no CADASTRO via %s", post_id, status, url)
        resp = requests.patch(url, json=payload, headers=headers, timeout=10)
        if 200 <= resp.status_code < 300:
            logger.info("Status do post %s atualizado para %s no CADASTRO.", post_id, status)
            return True
        else:
            logger.error("Falha ao atualizar status do post %s: %s %s", post_id, resp.status_code, resp.text)
            return False
    except Exception as e:
        logger.exception("Erro ao atualizar status do post %s: %s", post_id, e)
        return False


def sincronizar_dados_cadastro(payload: dict) -> bool:
    """Envia full_sync para o CADASTRO via PATCH /posts/<id>/sync"""
    cadastro_api_url = os.getenv("CADASTRO_API_URL", "http://rcee-cadastro:5000")
    cadastro_api_token = os.getenv("CADASTRO_API_TOKEN", "seu_token_aqui")
    post_id = payload.get("post_id")

    url = f"{cadastro_api_url.rstrip('/')}/posts/{post_id}/sync"
    headers = {
        "Authorization": f"Bearer {cadastro_api_token}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    try:
        logger.info("Sincronizando post %s no CADASTRO via %s", post_id, url)
        resp = requests.patch(url, json=payload, headers=headers, timeout=10)
        if 200 <= resp.status_code < 300:
            logger.info("Post %s sincronizado com sucesso no CADASTRO.", post_id)
            return True
        else:
            logger.error("Falha ao sincronizar post %s: %s %s", post_id, resp.status_code, resp.text)
            return False
    except Exception as e:
        logger.exception("Erro ao sincronizar post %s: %s", post_id, e)
        return False


def processar_mensagem_admin(msg_value: bytes):
    """
    Roteia mensagens do tópico post_status_update_admin por event_type:
      - full_sync     → sincroniza todos os dados via PATCH /posts/<id>/sync
      - status_update → atualiza apenas o status via PATCH /posts/<id>/status
    """
    payload = json.loads(msg_value.decode("utf-8"))
    post_id = payload.get("post_id")
    event_type = payload.get("event_type", "status_update")  # fallback para compatibilidade

    if not post_id:
        logger.warning("Mensagem inválida: falta post_id - payload=%s", payload)
        return False

    if event_type == "full_sync":
        return sincronizar_dados_cadastro(payload)

    elif event_type == "status_update":
        status = payload.get("status")
        if not status:
            logger.warning("Mensagem status_update sem status - payload=%s", payload)
            return False
        return atualizar_status_cadastro(post_id, status)

    else:
        logger.warning("event_type desconhecido: %s - payload=%s", event_type, payload)
        return False


# ---------------------------------------------------------------------------
# Loop principal
# ---------------------------------------------------------------------------

def main():
    if not DB_URL:
        logger.error("DATABASE_URL não configurada. Abortando.")
        return

    engine = create_engine(DB_URL)
    consumer = Consumer(KAFKA_CONFIG)
    consumer.subscribe(KAFKA_TOPICS)

    logger.info("Consumidor iniciado, escutando tópicos: %s", KAFKA_TOPICS)
    try:
        while not SHUTDOWN:
            try:
                msg = consumer.poll(1.0)
            except KafkaException as e:
                logger.exception("Erro no poll do Kafka: %s", e)
                continue

            if msg is None:
                continue

            if msg.error():
                logger.error("Mensagem com erro recebida: %s", msg.error())
                continue

            topic = msg.topic()
            processed = False

            try:
                if topic == "post_published":
                    process_message(engine, msg.value())
                    processed = True
                elif topic == "post_status_update_admin":
                    success = processar_mensagem_admin(msg.value())
                    processed = bool(success)
                else:
                    logger.warning("Tópico desconhecido: %s", topic)
                    processed = False
            except Exception as e:
                logger.exception("Erro ao processar mensagem do tópico %s: %s", topic, e)
                processed = False

            if processed:
                try:
                    consumer.commit(message=msg)
                    logger.debug(
                        "Offset comitado para tópico %s partition %s offset %s",
                        msg.topic(), msg.partition(), msg.offset()
                    )
                except Exception as e:
                    logger.exception("Falha ao comitar offset: %s", e)

    finally:
        try:
            consumer.close()
        except Exception:
            pass
        logger.info("Consumidor finalizado.")


if __name__ == "__main__":
    main()