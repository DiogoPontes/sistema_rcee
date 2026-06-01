from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, current_user
from .models import User, db
from .forms import LoginForm

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")

@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    form = LoginForm()

    if current_user.is_authenticated:
        return redirect(url_for("home"))

    if request.method == "POST":
        print("=== DEBUG LOGIN ===", flush=True)
        print("Form data:", dict(request.form), flush=True)
        print("validate_on_submit:", form.validate_on_submit(), flush=True)
        print("Form errors:", form.errors, flush=True)

        if form.errors:
            for field, erros in form.errors.items():
                print(f"  Campo '{field}': {erros}", flush=True)

        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "").strip()
        print("Email digitado:", email, flush=True)

        user = User.query.filter_by(email=email).first()
        print("Usuário encontrado:", user, flush=True)

        if user:
            resultado = user.check_password(password)
            print("check_password:", resultado, flush=True)
            print("is_active:", user.is_active, flush=True)
            print("role:", user.role, flush=True)

    if form.validate_on_submit():
        email = form.email.data.strip().lower()
        password = form.password.data.strip()
        user = User.query.filter_by(email=email).first()

        if user and user.check_password(password):
            if not user.is_active:
                flash("Sua conta está inativa. Entre em contato com o administrador.", "danger")
                return render_template("auth/login.html", form=form)
            login_user(user)
            flash(f"Bem-vindo(a), {user.name}!", "success")
            return redirect(url_for("home"))
        else:
            flash("Email ou senha incorretos.", "danger")

    return render_template("auth/login.html", form=form)

@auth_bp.route("/logout", methods=["GET", "POST"])
def logout():
    logout_user()
    flash("Você saiu com sucesso.", "info")
    return redirect(url_for("auth.login"))