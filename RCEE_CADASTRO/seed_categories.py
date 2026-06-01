from app import create_app
from app.models import db, Category

CATS = [
    ("Crime Organizado (CO)", "crime-organizado"),
    ("Tecnologias Inovadoras / Disruptivas", "tecnologias-inovadoras"),
    ("Eventos Climáticos Extremos", "eventos-climaticos"),
    ("Infraestruturas Críticas / Estratégicas", "infraestruturas-criticas"),
    ("Logística de Defesa – Base Industrial de Defesa (BID)", "logistica-defesa-bid"),
    ("Gestão Pública", "gestao-publica"),
    ("Conjunturas e Cenários", "conjunturas-cenarios"),
]

app = create_app()
with app.app_context():
    for name, slug in CATS:
        if not Category.query.filter_by(slug=slug).first():
            db.session.add(Category(name=name, slug=slug))
    db.session.commit()
    print("Categorias semeadas.")