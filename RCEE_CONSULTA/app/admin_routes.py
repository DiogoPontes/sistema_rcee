# app/admin_routes.py  
import os
import json
from datetime import datetime  
from confluent_kafka import Producer  
import logging
from flask import Blueprint, render_template, request, redirect, url_for, flash, abort, send_from_directory, current_app
from flask_login import login_required, current_user  
from .extensions import db  
from .models import Post, Category, PostStatus  
from .utils import slugify  
from sqlalchemy import or_  

logger = logging.getLogger(__name__)

# Configurações Kafka para o ADMIN (pegar do env)  
KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:29092")  
KAFKA_TOPIC_ADMIN_TO_CADASTRO = os.getenv("KAFKA_TOPIC_ADMIN_TO_CADASTRO", "post_status_update_admin")
  
_producer = None  
def get_kafka_producer():  
    global _producer  
    if _producer is None:  
        conf = {"bootstrap.servers": KAFKA_BOOTSTRAP_SERVERS}  
        _producer = Producer(conf)  
    return _producer  
  
def _delivery_report(err, msg):  
    if err:  
        logger.error("Erro entrega Kafka: %s", err)  
    else:  
        logger.info("Mensagem entregue: %s [%d] offset %s", msg.topic(), msg.partition(), msg.offset())

admin_bp = Blueprint("admin_bp", __name__, url_prefix="/admin")  
  
def require_admin():  
    """  
    Verifica se o usuário está autenticado e tem permissão de admin.  
    Retorna True se tiver permissão, False caso contrário.  
    """  
    if not current_user.is_authenticated:  
        return False  
      
    # Ajuste conforme seu controle de permissões  
    # Exemplo: verificar se tem role admin  
    if not getattr(current_user, "is_admin", False):  
        return False  
      
    return True  
  
@admin_bp.before_request  
@login_required  
def guard():  
    """  
    Protege todas as rotas do blueprint admin_bp.  
    Garante que apenas usuários autenticados e com permissão de admin acessem.  
    """  
    if not current_user.is_authenticated:  
        flash("Por favor, faça login para acessar esta área.", "warning")  
        return redirect(url_for("auth.login"))  
      
    if not require_admin():  
        flash("Você não tem permissão para acessar esta área.", "danger")  
        abort(403)  
  
@admin_bp.route("/conteudos", methods=["GET"])  
@login_required  
def list_conteudos():  
    """Lista todos os conteúdos com filtros e paginação."""  
    categories = Category.query.order_by(Category.name.asc()).all()  
  
    # Parâmetros de paginação e filtros  
    page = int(request.args.get("page", 1))  
    per_page = int(request.args.get("per_page", 10))  
    q = request.args.get("q", "").strip()  
    status = request.args.get("status", "").strip()  
    category_id = request.args.get("category_id", "").strip()  
  
    # Query base  
    query = Post.query  
  
    # Filtro de busca por texto  
    if q:  
        like = f"%{q}%"  
        query = query.filter(  
            or_(  
                Post.title.ilike(like),  
                Post.summary.ilike(like),  
                Post.slug.ilike(like)  
            )  
        )  
  
    # Filtro por status  
    if status in (PostStatus.DRAFT, PostStatus.PUBLISHED):  
        query = query.filter(Post.status == status)  
  
    # Filtro por categoria  
    if category_id.isdigit():  
        query = query.filter(Post.category_id == int(category_id))  
  
    # Ordenação  
    query = query.order_by(Post.published_at.desc(), Post.created_at.desc())  
  
    # Paginação  
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)  
  
    return render_template(  
        "admin/conteudos_list.html",  
        pagination=pagination,  
        posts=pagination.items,  
        q=q,  
        status=status,  
        category_id=category_id,  
        categories=categories,  
        PostStatus=PostStatus,  
    )  
  
@admin_bp.route("/conteudos/<int:post_id>/editar", methods=["GET", "POST"])  
@login_required  
def edit_conteudo(post_id):  
    """Edita um conteúdo existente."""  
    post = Post.query.get_or_404(post_id)  
    categories = Category.query.order_by(Category.name.asc()).all()  
  
    if request.method == "POST":  
        title = request.form.get("title", "").strip()  
        slug = request.form.get("slug", "").strip()  
        summary = request.form.get("summary", "").strip()  
        body = request.form.get("body", "").strip()  
        status = request.form.get("status", PostStatus.DRAFT)  
        category_id = request.form.get("category_id")  
  
        # Validação  
        if not title:  
            flash("Título é obrigatório.", "danger")  
            return render_template(  
                "admin/conteudo_form.html",  
                post=post,  
                categories=categories,  
                PostStatus=PostStatus  
            )  
  
        # Atualizar dados do post  
        post.title = title  
        post.slug = slugify(slug or title)  
        post.summary = summary  
        post.body = body  
        post.status = status  
        post.category_id = int(category_id) if category_id else None  
  
        # Definir data de publicação se mudou para publicado  
        if post.status == PostStatus.PUBLISHED and not post.published_at:  
            from datetime import datetime  
            post.published_at = datetime.utcnow()  
  
        db.session.commit()  
        flash("Conteúdo atualizado com sucesso.", "success")  
        return redirect(url_for("admin_bp.list_conteudos"))  
  
    return render_template(  
        "admin/conteudo_form.html",  
        post=post,  
        categories=categories,  
        PostStatus=PostStatus  
    )  
  
@admin_bp.route("/conteudos/<int:post_id>/excluir", methods=["POST"])
@login_required
def delete_conteudo(post_id):
    """Exclui um conteúdo (local) e solicita reprovação no CADASTRO via Kafka)."""
    post = Post.query.get_or_404(post_id)

    # 1) Publicar evento no tópico ADMIN -> CADASTRO solicitando alteração de status
    producer = get_kafka_producer()

    evento = {
        "post_id": post.id,
        "status": "disapproved",
        "requested_by": getattr(current_user, "id", None),
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }

    try:
        producer.produce(
            KAFKA_TOPIC_ADMIN_TO_CADASTRO,
            key=str(post.id),
            value=json.dumps(evento),
            callback=_delivery_report
        )
        # flush com timeout curto para garantir entrega síncrona (ajuste timeout se necessário)
        producer.flush(timeout=10.0)
    except Exception as e:
        logger.exception("Falha ao publicar evento Kafka para reprovação do post %s: %s", post.id, e)
        flash("Erro ao enviar solicitação de reprovação. A exclusão não foi realizada.", "danger")
        return redirect(url_for("admin_bp.list_conteudos"))

    # Se chegamos aqui, o evento foi enviado. Proceder com exclusão local (se essa é a política desejada).
    # Deletar todos os assets primeiro
    for asset in list(post.assets):  # copy to list para evitar issues ao iterar e deletar
        # Deletar arquivo físico se existir
        if asset.file_path and os.path.exists(asset.file_path):
            try:
                os.remove(asset.file_path)
            except Exception as e:
                logger.warning("Erro ao deletar arquivo %s: %s", asset.file_path, e)
        try:
            db.session.delete(asset)
        except Exception as e:
            logger.exception("Erro ao remover registro de asset id=%s: %s", getattr(asset, "id", None), e)

    # Finalmente, deletar o post localmente
    try:
        db.session.delete(post)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        logger.exception("Erro ao deletar post local id=%s: %s", post_id, e)
        flash("Erro ao deletar post localmente após solicitar reprovação.", "danger")
        return redirect(url_for("admin_bp.list_conteudos"))

    
    return redirect(url_for("admin_bp.list_conteudos"))

@admin_bp.route('/static/uploads/<path:filename>')  
def serve_uploads(filename):  
    uploads_dir = '/app/app/static/uploads'  # caminho absoluto dentro do container  
    return send_from_directory(uploads_dir, filename)