from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, current_user
from .models import User, db
from .forms import LoginForm  # ← Importar o LoginForm

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")

@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    """
    Tela de login - ÚNICA ROTA PÚBLICA.
    Após login bem-sucedido, redireciona SEMPRE para /home.
    """
    form = LoginForm()  # ← Criar instância do formulário
    
    # Se já estiver logado, redireciona direto para home
    if current_user.is_authenticated:
        return redirect(url_for("home"))
    
    # Validação do formulário (POST + CSRF)
    if form.validate_on_submit():
        email = form.email.data.strip().lower()
        password = form.password.data.strip()
        
        # Buscar usuário no banco
        user = User.query.filter_by(email=email).first()
        
        # Verificar credenciais
        if user and user.check_password(password):
            # Verificar se a conta está ativa
            if not user.is_active:
                flash("Sua conta está inativa. Entre em contato com o administrador.", "danger")
                return render_template("auth/login.html", form=form)
            
            # Fazer login
            login_user(user)
            flash(f"Bem-vindo(a), {user.name}!", "success")
            
            # ===== SEMPRE REDIRECIONA PARA /home =====
            return redirect(url_for("home"))
        else:
            flash("Email ou senha incorretos.", "danger")
    
    # Renderizar template COM o form
    return render_template("auth/login.html", form=form)

@auth_bp.route("/logout", methods=["GET", "POST"])
def logout():
    """Logout do usuário (aceita GET ou POST)."""
    logout_user()
    flash("Você saiu com sucesso.", "info")
    return redirect(url_for("auth.login"))