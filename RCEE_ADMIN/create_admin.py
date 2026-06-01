from app import create_app
from app.models import db, User, Role

app = create_app()
with app.app_context():
    email = input("Email do admin: ").strip().lower()
    name = input("Nome: ").strip()
    pwd = input("Senha: ").strip()
    if User.query.filter_by(email=email).first():
        print("Já existe usuário com esse email.")
    else:
        u = User(name=name, email=email, role=Role.ADMIN)
        u.set_password(pwd)
        db.session.add(u)
        db.session.commit()
        print("Admin criado.")