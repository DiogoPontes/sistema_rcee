# app/admin_routes.py  
import os
from flask import Blueprint, render_template, request, redirect, url_for, flash, abort  
from flask_login import login_required, current_user  
from .extensions import db  
from .models import Post, Category, PostStatus  
from .utils import slugify  
from sqlalchemy import or_  
  
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
    """Exclui um conteúdo."""  
    post = Post.query.get_or_404(post_id)  
      
    # Deletar todos os assets primeiro  
    for asset in post.assets:  
        # Deletar arquivo físico se existir  
        if asset.file_path and os.path.exists(asset.file_path):  
            try:  
                os.remove(asset.file_path)  
            except Exception as e:  
                print(f"Erro ao deletar arquivo: {e}")  
          
        db.session.delete(asset)  
      
    # Agora deletar o post  
    db.session.delete(post)  
    db.session.commit()  
      
    flash('Post deletado com sucesso!', 'success')  
    return redirect(url_for('admin_bp.list_conteudos'))