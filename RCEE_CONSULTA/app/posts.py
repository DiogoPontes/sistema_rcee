import os
import json
from datetime import datetime  
from confluent_kafka import Producer  
import logging
from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app, send_from_directory, abort, jsonify  
from flask_login import login_required, current_user  
from werkzeug.utils import secure_filename  
from .models import db, Post, Category, PostStatus, PostAsset, AssetType, Role  
from .forms import PostForm, AssetLinkForm, AssetUploadForm  
from .utils import allowed_file, sanitize_html, slugify  

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
  
posts_bp = Blueprint("posts", __name__, url_prefix="/posts")  
  
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
    if post.status != PostStatus.APPROVED:  
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
        
        # Tratar None para slug e título
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
            published_at=form.published_at.data or (datetime.utcnow() if form.status.data == PostStatus.APPROVED else None)    
        )    
        db.session.add(post)    
        db.session.commit()    
        flash("Conteúdo criado. Agora você pode adicionar links e anexos.", "success")    
        return redirect(url_for("posts.edit", post_id=post.id))  
          
    return render_template("posts/form.html", form=form, mode="new")  
  
@posts_bp.route("/<int:post_id>/edit", methods=["GET","POST"])  
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
        
        # Tratar None para slug
        slug_raw = form.slug.data or ""
        post.title = (form.title.data or "").strip()
        post.slug = slug_raw.strip() or slugify(post.title or "")
        post.summary = form.summary.data.strip() if form.summary.data else None  
        post.body = sanitize_html(form.body_html.data)  
        post.category_id = form.category_id.data  
        post.status = form.status.data  
        if post.status == PostStatus.APPROVED and not post.published_at:  
            post.published_at = datetime.utcnow()  
        post.published_at = form.published_at.data or post.published_at
        db.session.commit()  
        flash("Conteúdo atualizado.", "success")  
        return redirect(url_for("posts.edit", post_id=post.id))  
          
    link_form = AssetLinkForm()  
    upload_form = AssetUploadForm()  
    return render_template("posts/form.html", form=form, mode="edit", post=post, link_form=link_form, upload_form=upload_form, PostStatus=PostStatus)  
  
@posts_bp.route("/<int:post_id>/delete", methods=["POST"])
@login_required
def delete_post(post_id):
    post = Post.query.get_or_404(post_id)

    # Publicar evento Kafka para reprovar no CADASTRO
    producer = get_kafka_producer()

    evento = {
        "post_id": post.id,
        "status": "disapproved",
        "requested_by": getattr(current_user, "id", None),
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }

    try:
        logger.info(f"Enviando evento Kafka para reprovação do post {post.id}: {evento}")
        producer.produce(
            KAFKA_TOPIC_ADMIN_TO_CADASTRO,
            key=str(post.id),
            value=json.dumps(evento),
            callback=_delivery_report
        )
        producer.flush(timeout=10.0)
        logger.info("Evento Kafka enviado com sucesso.")
    except Exception as e:
        logger.exception("Falha ao publicar evento Kafka para reprovação do post %s: %s", post.id, e)
        flash("Erro ao enviar solicitação de reprovação. A exclusão não foi realizada.", "danger")
        return redirect(url_for("posts.list_posts"))

    # Se chegou aqui, evento enviado com sucesso, pode apagar localmente
    try:
        db.session.delete(post)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        logger.exception("Erro ao deletar post local id=%s: %s", post_id, e)
        flash("Erro ao deletar post localmente após solicitar reprovação.", "danger")
        return redirect(url_for("posts.list_posts"))

    flash("Registro Reprovado.", "success")
    return redirect(url_for("posts.list_posts"))
  
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
        except Exception as e:  
            pass  
      
    db.session.delete(asset)  
    db.session.commit()  
      
    # Retornar JSON se for requisição AJAX  
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':  
        return jsonify({'success': True, 'message': 'Anexo/link removido com sucesso.'})  
      
    flash("Anexo/link removido com sucesso.", "success")  
    return redirect(url_for("posts.edit", post_id=post.id))  
  
@posts_bp.route("/<int:post_id>/assets/link", methods=["POST"])  
@login_required  
def add_link(post_id):  
    require_editor()  
    post = Post.query.get_or_404(post_id)  
      
    # Verificar se é requisição AJAX  
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'  
      
    if is_ajax:  
        # Processar dados JSON  
        data = request.get_json()  
        asset_type = data.get('asset_type')  
        title = data.get('title') or None  
        url = data.get('url', '').strip()  
          
        if not url:  
            return jsonify({'success': False, 'message': 'URL é obrigatória.'}), 400  
          
        asset = PostAsset(  
            post_id=post.id,  
            asset_type=asset_type,  
            title=title,  
            url=url  
        )  
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
        # Processar formulário tradicional  
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
      
    asset_type = AssetType.PDF if ext.lower() == ".pdf" else (AssetType.IMAGE if ext.lower() in [".png",".jpg",".jpeg",".gif"] else AssetType.FILE)  
    asset = PostAsset(  
        post_id=post.id,  
        asset_type=asset_type,  
        title=title,  
        file_path=f"static/uploads/{filename}"  
    )  
    db.session.add(asset)  
    db.session.commit()  
      
    # Retornar JSON se for requisição AJAX  
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
  
@posts_bp.route("/download/<path:filename>")  
def download(filename):  
    folder = current_app.config["UPLOAD_FOLDER"]  
    return send_from_directory(folder, filename, as_attachment=True)