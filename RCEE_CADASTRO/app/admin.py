from flask import Blueprint, render_template, redirect, url_for, flash, request, abort
from flask_login import login_required, current_user
from .models import Post, Role, User, Category, db

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")

def require_admin():
    """
    Verifica se o usuário logado tem permissão de admin.
    Bloqueia Viewers e usuários não autenticados.
    """
    if not current_user.is_authenticated:
        abort(401)
    
    if current_user.role == Role.VIEWER:
        flash("Você não tem permissão para acessar o painel administrativo.", "danger")
        abort(403)
    
    if current_user.role != Role.ADMIN:
        flash("Você não tem permissão para acessar o painel administrativo.", "danger")
        abort(403)

@admin_bp.before_request
@login_required
def protect_admin_routes():
    """
    Protege TODAS as rotas do blueprint admin.
    Garante que apenas usuários autenticados e com role ADMIN acessem.
    """
    if not current_user.is_authenticated:
        flash("Por favor, faça login para acessar esta área.", "warning")
        return redirect(url_for("auth.login"))
    
    if current_user.role == Role.VIEWER:
        flash("Você não tem permissão para acessar o painel administrativo.", "danger")
        abort(403)
    
    if current_user.role != Role.ADMIN:
        flash("Você não tem permissão para acessar o painel administrativo.", "danger")
        abort(403)


# ==================== DASHBOARD ====================

@admin_bp.route("/")
@login_required
def dashboard():
    post_count = Post.query.count()
    user_count = User.query.count()
    category_count = Category.query.count()
    return render_template(
        "admin/dashboard.html",
        post_count=post_count,
        user_count=user_count,
        category_count=category_count
    )


# ==================== USUÁRIOS ====================

@admin_bp.route("/users", methods=["GET"])
@login_required
def users():
    """Lista todos os usuários - apenas para ADMIN."""
    users = User.query.order_by(User.created_at.desc()).all()
    return render_template("admin/users.html", users=users, Role=Role)


@admin_bp.route("/users/create", methods=["POST"])
@login_required
def create_user():
    """Cria um novo usuário - apenas para ADMIN."""
    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip().lower()
    role = request.form.get("role", Role.EDITOR).strip().lower()
    password = request.form.get("password", "").strip()
    instituicao = request.form.get("instituicao", "").strip()
    contato = request.form.get("contato", "").strip()

    # Validações básicas
    if not all([name, email, password]):
        flash("Nome, email e senha são obrigatórios.", "warning")
        return redirect(url_for("admin.users"))

    if User.query.filter_by(email=email).first():
        flash("Este email já está cadastrado.", "danger")
        return redirect(url_for("admin.users"))

    # Normalizar role
    role = role.capitalize()
    if role not in ["Admin", "Editor", "Viewer"]:
        flash("Perfil inválido.", "danger")
        return redirect(url_for("admin.users"))

    # Criar usuário com novos campos
    user = User(
        name=name,
        email=email,
        role=role,
        instituicao=instituicao or None,
        contato=contato or None,
    )
    user.set_password(password)
    db.session.add(user)
    db.session.commit()

    flash(f'Usuário "{name}" criado com sucesso!', "success")
    return redirect(url_for("admin.users"))


@admin_bp.route("/users/<int:user_id>/edit", methods=["GET", "POST"])
@login_required
def edit_user(user_id):
    """Edita um usuário existente - apenas para ADMIN."""
    user = User.query.get_or_404(user_id)

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        role = request.form.get("role")
        password = request.form.get("password", "").strip()
        instituicao = request.form.get("instituicao", "").strip()
        contato = request.form.get("contato", "").strip()

        # Validações
        if not all([name, email, role]):
            flash("Nome, email e perfil são obrigatórios.", "warning")
            return redirect(url_for("admin.edit_user", user_id=user_id))

        existing_user = User.query.filter_by(email=email).first()
        if existing_user and existing_user.id != user_id:
            flash("Este email já está sendo usado por outro usuário.", "danger")
            return redirect(url_for("admin.edit_user", user_id=user_id))

        role = role.capitalize()
        if role not in ["Admin", "Editor", "Viewer"]:
            flash("Perfil inválido.", "danger")
            return redirect(url_for("admin.edit_user", user_id=user_id))

        # Atualizar campos
        user.name = name
        user.email = email
        user.role = role
        user.instituicao = instituicao or None
        user.contato = contato or None

        if password:
            user.set_password(password)

        db.session.commit()
        flash(f'Usuário "{name}" atualizado com sucesso!', "success")
        return redirect(url_for("admin.users"))

    return render_template("admin/user_edit.html", user=user, Role=Role)


@admin_bp.route("/users/<int:user_id>/delete", methods=["POST"])
@login_required
def delete_user(user_id):
    """Exclui um usuário - apenas para ADMIN."""
    user = User.query.get_or_404(user_id)

    if user.id == current_user.id:
        flash("Você não pode excluir seu próprio usuário.", "warning")
        return redirect(url_for("admin.users"))

    user_name = user.name
    db.session.delete(user)
    db.session.commit()

    flash(f'Usuário "{user_name}" removido com sucesso.', "success")
    return redirect(url_for("admin.users"))


# ==================== CATEGORIAS ====================

@admin_bp.route("/categories", methods=["GET"])
@login_required
def categories():
    """Lista todas as categorias - apenas para ADMIN."""
    cats = Category.query.order_by(Category.name).all()
    return render_template("admin/categories.html", categories=cats)


@admin_bp.route("/categories/create", methods=["POST"])
@login_required
def create_category():
    """Cria uma nova categoria - apenas para ADMIN."""
    name = request.form.get("name", "").strip()
    slug = request.form.get("slug", "").strip()
    desc = request.form.get("description", "").strip()

    if not name or not slug:
        flash("Nome e slug são obrigatórios.", "warning")
        return redirect(url_for("admin.categories"))

    if Category.query.filter((Category.name == name) | (Category.slug == slug)).first():
        flash("Já existe uma categoria com este nome ou slug.", "danger")
        return redirect(url_for("admin.categories"))

    c = Category(name=name, slug=slug, description=desc)
    db.session.add(c)
    db.session.commit()

    flash(f'Categoria "{name}" criada com sucesso!', "success")
    return redirect(url_for("admin.categories"))


@admin_bp.route("/categories/<int:category_id>/edit", methods=["GET", "POST"])
@login_required
def edit_category(category_id):
    """Edita uma categoria existente - apenas para ADMIN."""
    category = Category.query.get_or_404(category_id)

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        slug = request.form.get("slug", "").strip()
        desc = request.form.get("description", "").strip()

        if not name or not slug:
            flash("Nome e slug são obrigatórios.", "warning")
            return redirect(url_for("admin.edit_category", category_id=category_id))

        existing = Category.query.filter(
            ((Category.name == name) | (Category.slug == slug)) &
            (Category.id != category_id)
        ).first()

        if existing:
            flash("Já existe outra categoria com este nome ou slug.", "danger")
            return redirect(url_for("admin.edit_category", category_id=category_id))

        category.name = name
        category.slug = slug
        category.description = desc

        db.session.commit()
        flash(f'Categoria "{name}" atualizada com sucesso!', "success")
        return redirect(url_for("admin.categories"))

    return render_template("admin/category_edit.html", category=category)


@admin_bp.route("/categories/<int:category_id>/delete", methods=["POST"])
@login_required
def delete_category(category_id):
    """Exclui uma categoria - apenas para ADMIN."""
    category = Category.query.get_or_404(category_id)

    if category.posts and len(category.posts) > 0:
        flash(f'Não é possível excluir a categoria "{category.name}" pois existem {len(category.posts)} publicações vinculadas a ela.', "warning")
        return redirect(url_for("admin.categories"))

    category_name = category.name
    db.session.delete(category)
    db.session.commit()

    flash(f'Categoria "{category_name}" removida com sucesso.', "success")
    return redirect(url_for("admin.categories"))