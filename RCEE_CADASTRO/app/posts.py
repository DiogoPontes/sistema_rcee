import os
from datetime import datetime
from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app, send_from_directory, abort, jsonify
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from .models import db, Post, Category, PostStatus, PostAsset, AssetType, Role
from .forms import PostForm, AssetLinkForm, AssetUploadForm
from .utils import allowed_file, sanitize_html, slugify
from confluent_kafka import Producer
from enum import EnumMeta
import json
import time
import logging

logger = logging.getLogger(__name__)

posts_bp = Blueprint("posts", __name__, url_prefix="/posts")

# ===== KAFKA - PRODUTOR GLOBAL =====
_kafka_producer = None

def get_kafka_producer(app):
    """
    Cria (uma vez) e reaproveita um Producer Kafka.
    Assim não criamos um Producer novo a cada request.
    """
    global _kafka_producer
    if _kafka_producer is None:
        if not app.config.get("KAFKA_BOOTSTRAP_SERVERS"):
            return None
        cfg = {
            "bootstrap.servers": app.config["KAFKA_BOOTSTRAP_SERVERS"],
            **app.config.get("KAFKA_PRODUCER_CONFIG", {})
        }
        _kafka_producer = Producer(cfg)
    return _kafka_producer


def publish_post_event(post):
    """
    Envia para o Kafka um evento indicando que este post foi publicado/atualizado.
    Se Kafka não estiver configurado, apenas loga e retorna.
    """
    app = current_app._get_current_object()
    producer = get_kafka_producer(app)
    if not producer:
        app.logger.warning("Kafka não configurado. Evento de publicação não será enviado.")
        return

    topic = app.config.get("KAFKA_POST_PUBLISHED_TOPIC", "post_published")

    assets_list = []
    for asset in post.assets:
        assets_list.append({
            "id": asset.id,
            "asset_type": asset.asset_type.value if hasattr(asset.asset_type, "value") else str(asset.asset_type),
            "title": asset.title,
            "url": asset.url,
            "file_path": asset.file_path,
        })

    payload = {
        "id": post.id,
        "title": post.title,
        "slug": post.slug,
        "summary": post.summary,
        "body": post.body,
        "featured_image": post.featured_image,
        "status": post.status.value if hasattr(post.status, "value") else post.status,
        "category_id": post.category_id,
        "author_id": post.author_id,
        "published_at": post.published_at.isoformat() if post.published_at else None,
        "created_at": post.created_at.isoformat() if post.created_at else None,
        "updated_at": post.updated_at.isoformat() if post.updated_at else None,
        "assets": assets_list,
        "event_ts": int(time.time() * 1000),
    }

    try:
        producer.produce(
            topic=topic,
            key=str(post.id),
            value=json.dumps(payload).encode("utf-8"),
        )
        producer.flush(0)
        app.logger.info(f"Evento de publicação enviado para Kafka: post_id={post.id}, assets={len(assets_list)}")
    except Exception as e:
        app.logger.error(f"Erro ao enviar evento para Kafka: {e}")

# ===== FIM KAFKA =====


def _convert_status(new_status_str):
    """
    Converte uma string para o tipo PostStatus correto.
    Tenta múltiplas estratégias para compatibilidade máxima.
    Retorna o valor convertido ou a string original como fallback.
    """
    # 1) Enum Python: PostStatus['NAME']
    try:
        if isinstance(PostStatus, EnumMeta):
            try:
                return PostStatus[new_status_str]
            except KeyError:
                pass
            try:
                return PostStatus(new_status_str)
            except Exception:
                pass
    except Exception:
        pass

    # 2) Chamada direta: PostStatus('value')
    try:
        return PostStatus(new_status_str)
    except Exception:
        pass

    # 3) Atributo: PostStatus.NAME
    try:
        if hasattr(PostStatus, new_status_str):
            return getattr(PostStatus, new_status_str)
    except Exception:
        pass

    # 4) Fallback: string direta
    return new_status_str


def require_editor():
    """Bloqueia acesso para usuários que não sejam Admin ou Editor"""
    if current_user.role == 'Viewer':
        abort(403)


@posts_bp.route("/")
@login_required
def list_posts():
    require_editor()
    posts = Post.query.order_by(Post.created_at.desc()).all()
    return render_template("posts/list.html", posts=posts, PostStatus=PostStatus)


@posts_bp.route("/<int:post_id>")
def detail(post_id):
    post = Post.query.get_or_404(post_id)
    if post.status != PostStatus.PUBLISHED:
        if not current_user.is_authenticated or (current_user.id != post.author_id and current_user.role not in (Role.ADMIN, Role.EDITOR)):
            abort(404)
    return render_template("posts/detail.html", post=post)


@posts_bp.route("/new", methods=["GET", "POST"])
@login_required
def new():
    require_editor()
    form = PostForm()
    form.category_id.choices = [(c.id, c.name) for c in Category.query.order_by(Category.name).all()]

    if form.validate_on_submit():
        filename = None
        uploaded = form.featured_image.data
        if uploaded and hasattr(uploaded, 'filename') and uploaded.filename != '':
            filename = secure_filename(uploaded.filename)
            folder = current_app.config["UPLOAD_FOLDER"]
            os.makedirs(folder, exist_ok=True)
            save_path = os.path.join(folder, filename)
            base, ext = os.path.splitext(filename)
            i = 1
            while os.path.exists(save_path):
                filename = f"{base}_{i}{ext}"
                save_path = os.path.join(folder, filename)
                i += 1
            uploaded.save(save_path)
            filename = f"static/uploads/{filename}"

        body_html = sanitize_html(form.body_html.data)
        slug_raw = form.slug.data or ""
        title_raw = form.title.data or ""
        slug = slug_raw.strip() or slugify(title_raw)

        if slug and Post.query.filter_by(slug=slug).first():
            slug = f"{slug}-{int(datetime.utcnow().timestamp())}"

        post = Post(
            title=title_raw.strip(),
            slug=slug,
            summary=form.summary.data.strip() if form.summary.data else None,
            body=body_html,
            category_id=form.category_id.data,
            author_id=current_user.id,
            status=form.status.data,
            featured_image=filename,
            published_at=form.published_at.data or (datetime.utcnow() if form.status.data == PostStatus.PUBLISHED else None)
        )
        db.session.add(post)
        db.session.commit()

        if post.status == PostStatus.PUBLISHED:
            publish_post_event(post)

        flash("Conteúdo criado. Agora você pode adicionar links e anexos.", "success")
        return redirect(url_for("posts.edit", post_id=post.id))

    return render_template("posts/form.html", form=form, mode="new")


@posts_bp.route("/<int:post_id>/edit", methods=["GET", "POST"])
@login_required
def edit(post_id):
    require_editor()
    post = Post.query.get_or_404(post_id)
    if current_user.role == Role.EDITOR and post.author_id != current_user.id:
        abort(403)

    form = PostForm(obj=post)
    form.category_id.choices = [(c.id, c.name) for c in Category.query.order_by(Category.name).all()]

    if request.method == "GET":
        form.body_html.data = post.body or ""

    if form.validate_on_submit():
        uploaded = form.featured_image.data
        if uploaded and hasattr(uploaded, 'filename') and uploaded.filename != '':
            filename = secure_filename(uploaded.filename)
            folder = current_app.config["UPLOAD_FOLDER"]
            os.makedirs(folder, exist_ok=True)
            save_path = os.path.join(folder, filename)
            base, ext = os.path.splitext(filename)
            i = 1
            while os.path.exists(save_path):
                filename = f"{base}_{i}{ext}"
                save_path = os.path.join(folder, filename)
                i += 1
            uploaded.save(save_path)
            post.featured_image = f"static/uploads/{filename}"

        slug_raw = form.slug.data or ""
        post.title = (form.title.data or "").strip()
        post.slug = slug_raw.strip() or slugify(post.title or "")
        post.summary = form.summary.data.strip() if form.summary.data else None
        post.body = sanitize_html(form.body_html.data)
        post.category_id = form.category_id.data
        post.status = form.status.data
        if post.status == PostStatus.PUBLISHED and not post.published_at:
            post.published_at = datetime.utcnow()
        post.published_at = form.published_at.data or post.published_at
        db.session.commit()

        if post.status == PostStatus.PUBLISHED:
            publish_post_event(post)

        flash("Conteúdo atualizado.", "success")
        return redirect(url_for("posts.edit", post_id=post.id))

    link_form = AssetLinkForm()
    upload_form = AssetUploadForm()
    return render_template("posts/form.html", form=form, mode="edit", post=post, link_form=link_form, upload_form=upload_form, PostStatus=PostStatus)


@posts_bp.route("/<int:post_id>/delete", methods=["POST"])
@login_required
def delete(post_id):
    require_editor()
    post = Post.query.get_or_404(post_id)
    if current_user.role == Role.EDITOR and post.author_id != current_user.id:
        abort(403)

    try:
        for asset in post.assets:
            if asset.file_path:
                try:
                    file_full_path = os.path.join(current_app.root_path, asset.file_path)
                    if os.path.exists(file_full_path):
                        os.remove(file_full_path)
                except Exception as e:
                    logger.warning("Erro ao deletar arquivo do asset: %s", e)

        if post.featured_image:
            try:
                featured_image_path = os.path.join(current_app.root_path, post.featured_image)
                if os.path.exists(featured_image_path):
                    os.remove(featured_image_path)
            except Exception as e:
                logger.warning("Erro ao deletar imagem destacada: %s", e)

        db.session.delete(post)
        db.session.commit()

        flash("Conteúdo excluído com sucesso.", "success")
        return redirect(url_for("index"))

    except Exception as e:
        db.session.rollback()
        logger.exception("Erro ao deletar post: %s", e)
        flash("Erro ao excluir conteúdo. Tente novamente.", "danger")
        return redirect(url_for("index"))


@posts_bp.route("/<int:post_id>/assets/<int:asset_id>/delete", methods=["POST"])
@login_required
def delete_asset(post_id, asset_id):
    require_editor()
    post = Post.query.get_or_404(post_id)
    asset = PostAsset.query.get_or_404(asset_id)

    if asset.post_id != post.id:
        abort(404)

    if current_user.role == Role.EDITOR and post.author_id != current_user.id:
        abort(403)

    if asset.file_path:
        try:
            file_full_path = os.path.join(current_app.root_path, asset.file_path)
            if os.path.exists(file_full_path):
                os.remove(file_full_path)
        except Exception:
            pass

    db.session.delete(asset)
    db.session.commit()

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'success': True, 'message': 'Anexo/link removido com sucesso.'})

    flash("Anexo/link removido com sucesso.", "success")
    return redirect(url_for("posts.edit", post_id=post.id))


@posts_bp.route("/<int:post_id>/assets/link", methods=["POST"])
@login_required
def add_link(post_id):
    require_editor()
    post = Post.query.get_or_404(post_id)
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

    if is_ajax:
        data = request.get_json()
        asset_type = data.get('asset_type')
        title = data.get('title') or None
        url = data.get('url', '').strip()

        if not url:
            return jsonify({'success': False, 'message': 'URL é obrigatória.'}), 400

        asset = PostAsset(post_id=post.id, asset_type=asset_type, title=title, url=url)
        db.session.add(asset)
        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Link adicionado.',
            'asset': {
                'id': asset.id,
                'title': asset.title or 'Sem título',
                'asset_type': asset.asset_type,
                'url': asset.url
            }
        })
    else:
        form = AssetLinkForm()
        if form.validate_on_submit():
            asset = PostAsset(
                post_id=post.id,
                asset_type=form.asset_type.data,
                title=form.title.data or None,
                url=form.url.data.strip()
            )
            db.session.add(asset)
            db.session.commit()
            flash("Link adicionado.", "success")
        else:
            flash("Falha ao adicionar link.", "danger")
        return redirect(url_for("posts.edit", post_id=post.id))


@posts_bp.route("/<int:post_id>/assets/upload", methods=["POST"])
@login_required
def add_upload(post_id):
    require_editor()
    post = Post.query.get_or_404(post_id)
    uploaded = request.files.get("file")
    title = request.form.get("title") or None

    if not uploaded or uploaded.filename == "":
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'message': 'Nenhum arquivo selecionado.'}), 400
        flash("Nenhum arquivo selecionado.", "warning")
        return redirect(url_for("posts.edit", post_id=post.id))

    if not allowed_file(uploaded.filename):
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'message': 'Tipo de arquivo não permitido.'}), 400
        flash("Tipo de arquivo não permitido.", "danger")
        return redirect(url_for("posts.edit", post_id=post.id))

    filename = secure_filename(uploaded.filename)
    folder = current_app.config["UPLOAD_FOLDER"]
    os.makedirs(folder, exist_ok=True)
    save_path = os.path.join(folder, filename)
    base, ext = os.path.splitext(filename)
    i = 1
    while os.path.exists(save_path):
        filename = f"{base}_{i}{ext}"
        save_path = os.path.join(folder, filename)
        i += 1
    uploaded.save(save_path)

    form_asset_type = request.form.get('asset_type')
    if form_asset_type == 'editor_media':
        asset_type = AssetType.EDITOR_MEDIA
    else:
        asset_type = AssetType.PDF if ext.lower() == ".pdf" else (AssetType.IMAGE if ext.lower() in [".png", ".jpg", ".jpeg", ".gif"] else AssetType.FILE)

    asset = PostAsset(
        post_id=post.id,
        asset_type=asset_type,
        title=title,
        file_path=f"static/uploads/{filename}"
    )
    db.session.add(asset)
    db.session.commit()

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({
            'success': True,
            'message': 'Arquivo anexado.',
            'asset': {
                'id': asset.id,
                'title': asset.title or 'Sem título',
                'asset_type': asset.asset_type,
                'file_path': asset.file_path
            }
        })

    flash("Arquivo anexado.", "success")
    return redirect(url_for("posts.edit", post_id=post.id))


@posts_bp.route("/<int:post_id>/assets/carousel-upload", methods=["POST"])
@login_required
def carousel_upload(post_id):
    """Upload de imagem para carrossel — NÃO aparece nos Itens Salvos."""
    require_editor()
    post = Post.query.get_or_404(post_id)
    uploaded = request.files.get("file")

    if not uploaded or uploaded.filename == "":
        return jsonify({'success': False, 'message': 'Nenhum arquivo selecionado.'}), 400

    if not allowed_file(uploaded.filename):
        return jsonify({'success': False, 'message': 'Tipo de arquivo não permitido.'}), 400

    filename = secure_filename(uploaded.filename)
    folder = current_app.config["UPLOAD_FOLDER"]
    os.makedirs(folder, exist_ok=True)
    save_path = os.path.join(folder, filename)
    base, ext = os.path.splitext(filename)
    i = 1
    while os.path.exists(save_path):
        filename = f"{base}_{i}{ext}"
        save_path = os.path.join(folder, filename)
        i += 1
    uploaded.save(save_path)

    asset = PostAsset(
        post_id=post.id,
        asset_type=AssetType.CAROUSEL,
        title=request.form.get("title") or ('Carrossel - ' + filename),
        file_path=f"static/uploads/{filename}"
    )
    db.session.add(asset)
    db.session.commit()

    return jsonify({
        'success': True,
        'asset': {
            'id': asset.id,
            'file_path': asset.file_path
        }
    })


@posts_bp.route("/download/<path:filename>")
def download(filename):
    folder = current_app.config["UPLOAD_FOLDER"]
    return send_from_directory(folder, filename, as_attachment=True)


# ---------------------------------------------------------------------------
# Endpoints para o Consumer Kafka do ADMIN
# ---------------------------------------------------------------------------

@posts_bp.route("/<int:post_id>/status", methods=["PATCH"])
def update_status_api(post_id):
    """
    Recebe event_type=status_update do consumer ADMIN.
    Atualiza apenas o status do post.
    Autenticado por token Bearer (CADASTRO_API_TOKEN no .env).
    """
    # Validação do token
    api_token = current_app.config.get("CADASTRO_API_TOKEN") or os.getenv("CADASTRO_API_TOKEN")
    auth_header = request.headers.get("Authorization", "")
    if api_token and auth_header != f"Bearer {api_token}":
        return jsonify({"error": "Unauthorized"}), 401

    post = Post.query.get_or_404(post_id)
    data = request.get_json(silent=True) or {}
    new_status_str = data.get("status")

    if not new_status_str:
        return jsonify({"error": "Status não fornecido"}), 400

    current_app.logger.debug(
        "update_status_api: PostStatus tipo=%s, post.status atual=%s",
        type(PostStatus), getattr(post, "status", None)
    )

    new_status = _convert_status(new_status_str)

    try:
        post.status = new_status
        db.session.commit()
        current_app.logger.info("Post %s atualizado para %s via /status.", post_id, new_status_str)
        return jsonify({"success": True, "new_status": str(new_status)}), 200
    except Exception as e:
        db.session.rollback()
        current_app.logger.exception("Falha ao salvar status %s para post %s: %s", new_status_str, post_id, e)
        return jsonify({"error": str(e)}), 500


@posts_bp.route("/<int:post_id>/sync", methods=["PATCH"])
def sync_post(post_id):
    """
    Recebe event_type=full_sync do consumer ADMIN.
    Sincroniza todos os campos do post (title, slug, body, status, etc.).
    Autenticado por token Bearer (CADASTRO_API_TOKEN no .env).
    Cria o post localmente se ainda não existir.
    """
    # Validação do token
    api_token = current_app.config.get("CADASTRO_API_TOKEN") or os.getenv("CADASTRO_API_TOKEN")
    auth_header = request.headers.get("Authorization", "")
    if api_token and auth_header != f"Bearer {api_token}":
        return jsonify({"error": "Unauthorized"}), 401

    payload = request.get_json(force=True)
    if not payload:
        return jsonify({"error": "Payload vazio"}), 400

    post = Post.query.get(post_id)
    if not post:
        # Cria o post se ainda não existir no CADASTRO
        post = Post(id=post_id)
        db.session.add(post)
        current_app.logger.info("Post %s não encontrado — criando via full_sync.", post_id)

    post.title          = payload.get("title", post.title)
    post.slug           = payload.get("slug", post.slug)
    post.summary        = payload.get("summary", post.summary)
    post.body           = payload.get("body", post.body)
    post.featured_image = payload.get("featured_image", post.featured_image)
    post.category_id    = payload.get("category_id", post.category_id)

    raw_status = payload.get("status")
    if raw_status:
        post.status = _convert_status(raw_status)

    try:
        db.session.commit()
        current_app.logger.info("Post %s sincronizado via /sync.", post_id)
        return jsonify({"success": True, "post_id": post_id}), 200
    except Exception as e:
        db.session.rollback()
        current_app.logger.exception("Falha ao sincronizar post %s: %s", post_id, e)
        return jsonify({"error": str(e)}), 500