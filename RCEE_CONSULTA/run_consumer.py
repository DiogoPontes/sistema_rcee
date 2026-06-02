#!/usr/bin/env python3
"""
Consumidor Kafka -> rcee_consulta
Escuta tópicos configurados e faz upsert/delete no banco do CONSULTA.
"""

import os
import json
import signal
import logging
import requests
from datetime import datetime
from confluent_kafka import Consumer, KafkaException
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# Carrega .env.consumer
here = os.path.dirname(os.path.abspath(__file__))
env_path = os.path.join(here, ".env.consumer")
load_dotenv(env_path)

# Configurações (padronizadas para os valores que o producer usa)
KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")
# Permite múltiplos tópicos separados por vírgula. Defaults incluem o tópico do admin.
KAFKA_TOPICS = [t.strip() for t in os.getenv("KAFKA_TOPIC", "post_status_update_admin,post_approved").split(",") if t.strip()]
KAFKA_GROUP_ID = os.getenv("KAFKA_GROUP_ID", "sync-rcee-consulta")
DB_URL = os.getenv("DATABASE_URL")

# Configurações de Assets (HTTP)
ASSETS_ENABLED = os.getenv("ASSETS_ENABLED", "true").lower() in ("1", "true", "yes")
UPLOADS_ADMIN_BASE_URL = os.getenv("UPLOADS_ADMIN_BASE_URL", "http://rcee-admin:5000")
CONSULTA_UPLOADS_PATH = os.getenv("CONSULTA_UPLOADS_PATH", "/app/app/static/uploads")
MAX_ASSET_RETRIES = int(os.getenv("MAX_ASSET_RETRIES", "3"))
ASSET_DOWNLOAD_TIMEOUT = int(os.getenv("ASSET_DOWNLOAD_TIMEOUT", "30"))
FAIL_ON_ASSET_ERROR = os.getenv("FAIL_ON_ASSET_ERROR", "false").lower() in ("1", "true", "yes")

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s:%(name)s:%(message)s")
logger = logging.getLogger("sync-rcee-consulta")

KAFKA_CONFIG = {
    "bootstrap.servers": KAFKA_BOOTSTRAP_SERVERS,
    "group.id": KAFKA_GROUP_ID,
    "auto.offset.reset": "earliest",
    "enable.auto.commit": False,
}

SHUTDOWN = False

def handle_signal(signum, frame):
    global SHUTDOWN
    logger.info("Sinal %s recebido. Encerrando...", signum)
    SHUTDOWN = True

signal.signal(signal.SIGTERM, handle_signal)
signal.signal(signal.SIGINT, handle_signal)


def download_asset(file_path: str) -> str | None:
    """
    Baixa um arquivo do ADMIN via HTTP e salva no volume do CONSULTA.
    Retorna o caminho relativo recebido (sem alteração) em caso de sucesso, ou None.
    """
    if not ASSETS_ENABLED or not file_path:
        return file_path

    filename = os.path.basename(file_path)
    dest_path = os.path.join(CONSULTA_UPLOADS_PATH, filename)

    if os.path.exists(dest_path):
        logger.debug("Asset já existe localmente: %s", dest_path)
        return file_path

    url = f"{UPLOADS_ADMIN_BASE_URL}/{file_path.lstrip('/')}"
    os.makedirs(CONSULTA_UPLOADS_PATH, exist_ok=True)

    for attempt in range(1, MAX_ASSET_RETRIES + 1):
        try:
            resp = requests.get(url, timeout=ASSET_DOWNLOAD_TIMEOUT)
            if resp.status_code == 200:
                with open(dest_path, "wb") as f:
                    f.write(resp.content)
                logger.info("Asset baixado: %s -> %s", url, dest_path)
                return file_path
            else:
                logger.warning("Tentativa %s/%s: HTTP %s para %s", attempt, MAX_ASSET_RETRIES, resp.status_code, url)
        except Exception as e:
            logger.warning("Tentativa %s/%s: erro ao baixar %s: %s", attempt, MAX_ASSET_RETRIES, url, e)

    logger.error("Falha ao baixar asset após %s tentativas: %s", MAX_ASSET_RETRIES, url)
    if FAIL_ON_ASSET_ERROR:
        raise RuntimeError(f"Falha ao baixar asset: {url}")
    return file_path


def parse_dt(val):
    if not val:
        return None
    try:
        return datetime.fromisoformat(val.replace("Z", "+00:00"))
    except Exception:
        return None


def do_delete_post(conn, post_id):
    # Deleta assets primeiro para respeitar FK
    conn.execute(text("DELETE FROM post_asset WHERE post_id = :id"), {"id": post_id})
    conn.execute(text("DELETE FROM post WHERE id = :id"), {"id": post_id})
    logger.info("Post %s removido do CONSULTA.", post_id)


def upsert_post(conn, data, featured_image_processed):
    post_id = int(data.get("post_id") or data.get("id"))
    category_id = data.get("category_id")

    # Garante que a categoria existe
    if category_id:
        existing_cat = conn.execute(text("SELECT id FROM category WHERE id = :id"), {"id": category_id}).fetchone()
        if not existing_cat:
            conn.execute(
                text("INSERT INTO category (id, name, slug) VALUES (:id, :name, :slug)"),
                {"id": category_id, "name": f"Categoria {category_id}", "slug": f"categoria-{category_id}"}
            )
            logger.info("Categoria %s criada automaticamente.", category_id)

    existing = conn.execute(text("SELECT id FROM post WHERE id = :id"), {"id": post_id}).fetchone()

    published_at = parse_dt(data.get("published_at"))
    created_at = parse_dt(data.get("created_at")) or datetime.utcnow()
    updated_at = parse_dt(data.get("updated_at"))

    if existing:
        conn.execute(text("""
            UPDATE post SET
                title        = :title,
                slug         = :slug,
                summary      = :summary,
                body         = :body,
                featured_image = :featured_image,
                status       = :status,
                category_id  = :category_id,
                author_id    = :author_id,
                published_at = :published_at,
                updated_at   = :updated_at
            WHERE id = :id
        """), {
            "id": post_id,
            "title": data.get("title"),
            "slug": data.get("slug"),
            "summary": data.get("summary"),
            "body": data.get("body"),
            "featured_image": featured_image_processed,
            "status": data.get("status", "approved"),
            "category_id": category_id,
            "author_id": data.get("author_id"),
            "published_at": published_at,
            "updated_at": updated_at,
        })
        logger.info("Post %s atualizado no CONSULTA.", post_id)
    else:
        conn.execute(text("""
            INSERT INTO post
                (id, title, slug, summary, body, featured_image, status,
                 category_id, author_id, published_at, created_at, updated_at)
            VALUES
                (:id, :title, :slug, :summary, :body, :featured_image, :status,
                 :category_id, :author_id, :published_at, :created_at, :updated_at)
        """), {
            "id": post_id,
            "title": data.get("title"),
            "slug": data.get("slug"),
            "summary": data.get("summary"),
            "body": data.get("body"),
            "featured_image": featured_image_processed,
            "status": data.get("status", "approved"),
            "category_id": category_id,
            "author_id": data.get("author_id"),
            "published_at": published_at,
            "created_at": created_at,
            "updated_at": updated_at,
        })
        logger.info("Post %s criado no CONSULTA.", post_id)


def process_message(engine, raw_value: bytes):
    """Processa uma mensagem (raw bytes)."""
    try:
        data = json.loads(raw_value.decode("utf-8"))
    except Exception as e:
        logger.error("Falha ao decodificar mensagem: %s", e)
        return False

    event_type = data.get("event_type", "")
    post_id = data.get("id") or data.get("post_id")
    status = (data.get("status") or "").lower()

    if not post_id:
        logger.warning("Mensagem sem post_id, ignorando: %s", data)
        return True  # consider message processed to avoid re-delivery

    logger.info("Recebido evento '%s' para post_id=%s (status=%s)", event_type, post_id, status)

    # Tratamento:
    # - full_sync: somente faz upsert quando status == 'approved'
    # - status_update: se for reprovação/exclusão -> deleta ; se for aprovação -> tenta upsert se houver dados, senão ignora/espera full_sync
    try:
        with engine.begin() as conn:
            # Se for full_sync e estiver aprovado -> upsert
            if event_type == "full_sync":
                if status == "approved":
                    featured_image = data.get("featured_image")
                    featured_image_processed = None
                    if featured_image:
                        featured_image_processed = download_asset(featured_image)
                    upsert_post(conn, data, featured_image_processed)

                    # Upsert assets
                    assets = data.get("assets", []) or []
                    for asset in assets:
                        asset_id = asset.get("id")
                        if not asset_id:
                            continue
                        asset_file_path = asset.get("file_path")
                        if asset_file_path:
                            asset_file_path = download_asset(asset_file_path)
                        existing_asset = conn.execute(text("SELECT id FROM post_asset WHERE id = :id"), {"id": asset_id}).fetchone()
                        if existing_asset:
                            conn.execute(text("""
                                UPDATE post_asset SET
                                    asset_type = :asset_type,
                                    title      = :title,
                                    url        = :url,
                                    file_path  = :file_path
                                WHERE id = :id
                            """), {
                                "id": asset_id,
                                "asset_type": asset.get("asset_type"),
                                "title": asset.get("title"),
                                "url": asset.get("url"),
                                "file_path": asset_file_path,
                            })
                        else:
                            conn.execute(text("""
                                INSERT INTO post_asset (id, post_id, asset_type, title, url, file_path)
                                VALUES (:id, :post_id, :asset_type, :title, :url, :file_path)
                            """), {
                                "id": asset_id,
                                "post_id": post_id,
                                "asset_type": asset.get("asset_type"),
                                "title": asset.get("title"),
                                "url": asset.get("url"),
                                "file_path": asset_file_path,
                            })
                    logger.info("Assets do post %s sincronizados (%s itens).", post_id, len(assets))
                else:
                    logger.info("Evento full_sync recebido com status '%s' — ignorando (não cria/remova).", status)
            elif event_type == "status_update":
                # statuses que indicam remoção/reprovação — normalize palavras comuns
                if status in ("disapproved", "reproved", "reprovado", "rejected", "rejected_by_admin"):
                    logger.info("Status de reprovação recebido para post %s — removendo do CONSULTA.", post_id)
                    do_delete_post(conn, post_id)
                elif status == "approved":
                    # Se a mensagem tiver campos suficientes (title/body), faz upsert. Caso contrário, espera full_sync.
                    if data.get("title") or data.get("body") or data.get("slug"):
                        featured_image = data.get("featured_image")
                        featured_image_processed = None
                        if featured_image:
                            featured_image_processed = download_asset(featured_image)
                        upsert_post(conn, data, featured_image_processed)
                        logger.info("Status_update 'approved' com dados parciais: upsert realizado para %s", post_id)
                    else:
                        logger.info("Status_update 'approved' sem dados completos para %s — aguardando full_sync.", post_id)
                else:
                    # outro status — não vamos deletar por segurança (evita remoção em estados intermediários)
                    logger.info("Status_update recebido com status='%s' — sem ação (para evitar remoção acidental).", status)
            else:
                # Tópico/Evento desconhecido: tentar processar como full_sync se contiver dados
                if data.get("title") or data.get("body"):
                    logger.info("Evento desconhecido '%s' mas contém dados — realizando upsert.", event_type)
                    featured_image = data.get("featured_image")
                    featured_image_processed = None
                    if featured_image:
                        featured_image_processed = download_asset(featured_image)
                    upsert_post(conn, data, featured_image_processed)
                else:
                    logger.info("Evento desconhecido '%s' sem dados úteis — ignorando.", event_type)
        return True
    except Exception as e:
        logger.exception("Erro ao aplicar mudanças no DB para post %s: %s", post_id, e)
        return False


def main():
    if not DB_URL:
        logger.error("DATABASE_URL não configurada. Abortando.")
        return

    engine = create_engine(DB_URL)
    consumer = Consumer(KAFKA_CONFIG)
    consumer.subscribe(KAFKA_TOPICS)

    logger.info("Consumidor CONSULTA iniciado, escutando tópicos: %s", KAFKA_TOPICS)

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
                logger.error("Mensagem com erro: %s", msg.error())
                continue

            topic = msg.topic()
            processed = False

            try:
                # Processa independentemente do tópico: a função process_message decide ação baseada no event_type e status
                processed = process_message(engine, msg.value())
            except Exception as e:
                logger.exception("Erro ao processar mensagem do tópico %s: %s", topic, e)
                processed = False

            if processed:
                try:
                    consumer.commit(message=msg)
                    logger.debug(
                        "Offset comitado: tópico=%s partition=%s offset=%s",
                        msg.topic(), msg.partition(), msg.offset()
                    )
                except Exception as e:
                    logger.exception("Falha ao comitar offset: %s", e)

    finally:
        try:
            consumer.close()
        except Exception:
            pass
        logger.info("Consumidor CONSULTA finalizado.")


if __name__ == "__main__":
    main()