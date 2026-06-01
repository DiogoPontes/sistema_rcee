from confluent_kafka import Producer
import json
import os
import logging
from datetime import datetime

logger = logging.getLogger("admin_kafka_producer")
logging.basicConfig(level=logging.INFO)

KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")
KAFKA_TOPIC_ADMIN_TO_CADASTRO = os.getenv("KAFKA_TOPIC_ADMIN_TO_CADASTRO", "post_status_update_admin")

producer_conf = {
    "bootstrap.servers": KAFKA_BOOTSTRAP_SERVERS,
}

producer = Producer(producer_conf)


def delivery_report(err, msg):
    if err is not None:
        logger.error(f"Falha ao enviar mensagem: {err}")
    else:
        logger.info(f"Mensagem entregue em {msg.topic()} [{msg.partition()}] offset {msg.offset()}")


def publicar_status_reprovado(post_id, usuario_id):
    """Publica evento de reprovação (disapproved) para o CADASTRO."""
    evento = {
        "event_type": "status_update",
        "post_id": post_id,
        "status": "disapproved",
        "requested_by": usuario_id,
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }
    try:
        producer.produce(
            KAFKA_TOPIC_ADMIN_TO_CADASTRO,
            key=str(post_id),
            value=json.dumps(evento),
            callback=delivery_report
        )
        producer.flush(timeout=10.0)
        logger.info(f"Evento de reprovação publicado para post {post_id}")
        return True
    except Exception as e:
        logger.error(f"Erro ao publicar evento Kafka: {e}")
        return False


def publicar_sync_completo(post):
    """
    Publica evento com todos os dados do post para sincronização completa no CADASTRO.
    Chamado quando o Admin edita título, corpo, slug, etc.
    """
    evento = {
        "event_type": "full_sync",
        "post_id": post.id,
        "title": post.title,
        "slug": post.slug,
        "summary": post.summary,
        "body": post.body,
        "featured_image": post.featured_image,
        "category_id": post.category_id,
        "status": post.status.name if hasattr(post.status, "name") else str(post.status),
        "updated_at": datetime.utcnow().isoformat() + "Z"
    }
    try:
        producer.produce(
            KAFKA_TOPIC_ADMIN_TO_CADASTRO,
            key=str(post.id),
            value=json.dumps(evento),
            callback=delivery_report
        )
        producer.flush(timeout=10.0)
        logger.info(f"Evento full_sync publicado para post {post.id}")
        return True
    except Exception as e:
        logger.error(f"Erro ao publicar full_sync para post {post.id}: {e}")
        return False