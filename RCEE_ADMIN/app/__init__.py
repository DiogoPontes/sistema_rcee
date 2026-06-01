import os
from flask import Flask, redirect, url_for, render_template, request, flash, jsonify
from flask_login import login_required, current_user
from .models import db, login_manager, Post, Category, PostStatus
from flask_migrate import Migrate
from .auth import auth_bp
from .posts import posts_bp
from .categories import categories_bp
from .admin import admin_bp
from .utils import ensure_upload_folder
from config import config
from datetime import datetime, timedelta

def format_datetime(value, fmt="%d/%m/%Y %H:%M"):
    """Filtro Jinja para formatar datas."""
    if not value:
        return "-"
    if isinstance(value, str):
        try:
            value = datetime.fromisoformat(value)
        except Exception:
            return value
    return value.strftime(fmt)

def create_app(config_name="default"):
    """Cria e configura a aplicação Flask."""
    
    app = Flask(__name__, static_folder="static", template_folder="templates")
    app.config.from_object(config[config_name])

    # Limite de upload: 700 MB
    app.config['MAX_CONTENT_LENGTH'] = 700 * 1024 * 1024

    # Inicializar extensões
    db.init_app(app)
    Migrate(app, db)
    login_manager.init_app(app)

    # ===== CONFIGURAÇÃO CRÍTICA DO LOGIN =====
    login_manager.login_view = "auth.login"
    login_manager.login_message = "Por favor, faça login para acessar esta página."
    login_manager.login_message_category = "warning"
    
    # Garantir que a pasta de uploads existe
    ensure_upload_folder(app.config["UPLOAD_FOLDER"])

    # Registrar blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(posts_bp)
    app.register_blueprint(categories_bp)
    app.register_blueprint(admin_bp)

    # ===== ROTA RAIZ - REDIRECIONA PARA LOGIN OU HOME =====
    @app.route("/")
    def index():
        """
        Rota raiz - redireciona automaticamente.
        - Se NÃO estiver logado: redireciona para LOGIN
        - Se estiver logado: redireciona para HOME
        """
        if current_user.is_authenticated:
            return redirect(url_for("home"))
        return redirect(url_for("auth.login"))

    # ===== ROTA HOME - PROTEGIDA COM FILTROS =====
    @app.route("/home")
    @login_required
    def home():
        """Página inicial com listagem de posts publicados e filtros."""
        
        # Capturar parâmetros de filtro da URL
        category_id = request.args.get('category_id', type=int)
        title_search = request.args.get('title', '').strip()
        text_search = request.args.get('text', '').strip()
        date_from = request.args.get('date_from', '').strip()
        date_to = request.args.get('date_to', '').strip()

        # Query base: apenas posts publicados
        query = Post.query.filter(  
            Post.status.in_([PostStatus.PUBLISHED, PostStatus.APPROVED])  
        )

        # Filtro por categoria
        if category_id:
            query = query.filter_by(category_id=category_id)

        # Filtro por título (busca parcial, case-insensitive)
        if title_search:
            query = query.filter(Post.title.ilike(f'%{title_search}%'))

        # Filtro por texto (busca no corpo do post)
        if text_search:
            query = query.filter(Post.body.ilike(f'%{text_search}%'))

        # Filtro por data inicial
        if date_from:
            try:
                date_from_obj = datetime.strptime(date_from, '%Y-%m-%d')
                query = query.filter(Post.published_at >= date_from_obj)
            except ValueError:
                pass

        # Filtro por data final
        if date_to:
            try:
                date_to_obj = datetime.strptime(date_to, '%Y-%m-%d')
                # Adiciona 23:59:59 para incluir todo o dia
                date_to_obj = date_to_obj + timedelta(days=1) - timedelta(seconds=1)
                query = query.filter(Post.published_at <= date_to_obj)
            except ValueError:
                pass

        # Ordenar por data de publicação (mais recente primeiro)
        posts = query.order_by(Post.published_at.desc()).all()

        # Buscar todas as categorias para o filtro
        categories = Category.query.order_by(Category.name).all()

        return render_template(
            "index.html",
            posts=posts,
            categories=categories,
            filters={
                'category_id': category_id,
                'title': title_search,
                'text': text_search,
                'date_from': date_from,
                'date_to': date_to
            },
            PostStatus=PostStatus
        )

    # ===== FILTROS JINJA =====
    app.jinja_env.filters['datetime'] = format_datetime

    # ===== TRATAMENTO DE ERROS =====
    @app.errorhandler(401)
    def unauthorized(error):
        """Erro 401 - Não autenticado."""
        flash("Você precisa fazer login para acessar esta página.", "warning")
        return redirect(url_for("auth.login"))

    @app.errorhandler(403)
    def forbidden(error):
        """Erro 403 - Sem permissão."""
        return render_template("errors/403.html"), 403

    @app.errorhandler(404)
    def not_found(error):
        """Erro 404 - Página não encontrada."""
        return render_template("errors/404.html"), 404

    @app.errorhandler(413)
    def request_entity_too_large(error):
        """Erro 413 - Arquivo muito grande."""
        if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({
                'success': False,
                'message': 'O arquivo é muito grande. O limite é de 200MB.'
            }), 413
        flash("O arquivo é muito grande. O limite é de 200MB.", "danger")
        return redirect(url_for("home"))

    @app.errorhandler(500)
    def internal_error(error):
        """Erro 500 - Erro interno do servidor."""
        db.session.rollback()
        return render_template("errors/500.html"), 500

    return app