# app/categories.py
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required
from .models import db, Category
from .utils import slugify

# 1) Criar o blueprint PRIMEIRO
categories_bp = Blueprint("categories", __name__, url_prefix="/admin")

# 2) Depois definir as rotas

@categories_bp.route("/categories")
@login_required
def list_categories():  
    from flask import current_app  
  
    with current_app.app_context():  
        categories = Category.query.all()  
        print(f"DEBUG na rota: {len(categories)} categorias")  
        for c in categories:  
            print(f"  - {c.id}: {c.name}")  
  
    return render_template("admin/categories.html", categories=categories)

@categories_bp.route("/categories/criar", methods=["POST"])
@login_required
def create_category():
    name = request.form.get("name", "").strip()
    slug = request.form.get("slug", "").strip()
    description = request.form.get("description", "").strip()

    if not name:
        flash("Nome é obrigatório.", "danger")
        return redirect(url_for("categories.list_categories"))

    category = Category(
        name=name,
        slug=slugify(slug or name),
        description=description or None,
    )
    db.session.add(category)
    db.session.commit()
    flash("Categoria criada com sucesso.", "success")
    return redirect(url_for("categories.list_categories"))

@categories_bp.route("/categories/<int:category_id>/editar", methods=["GET", "POST"])
@login_required
def edit_category(category_id):
    category = Category.query.get_or_404(category_id)

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        slug = request.form.get("slug", "").strip()
        description = request.form.get("description", "").strip()

        if not name:
            flash("Nome é obrigatório.", "danger")
            return render_template("admin/category_form.html", category=category)

        category.name = name
        category.slug = slugify(slug or name)
        category.description = description or None

        db.session.commit()
        flash("Categoria atualizada com sucesso.", "success")
        return redirect(url_for("categories.list_categories"))

    return render_template("admin/category_form.html", category=category)

@categories_bp.route("/categories/<int:category_id>/excluir", methods=["POST"])
@login_required
def delete_category(category_id):
    category = Category.query.get_or_404(category_id)
    db.session.delete(category)
    db.session.commit()
    flash("Categoria excluída com sucesso.", "success")
    return redirect(url_for("categories.list_categories"))