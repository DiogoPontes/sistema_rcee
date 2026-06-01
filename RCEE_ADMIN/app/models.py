from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin, LoginManager
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()
login_manager = LoginManager()
login_manager.login_view = "auth.login"

class Role:
    ADMIN = "Admin"
    EDITOR = "Editor"
    VIEWER = "Viewer"

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), default=Role.VIEWER, nullable=False)
    instituicao = db.Column(db.String(100))
    contato = db.Column(db.String(20))
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, pwd: str):
        self.password_hash = generate_password_hash(pwd)

    def check_password(self, pwd: str) -> bool:
        return check_password_hash(self.password_hash, pwd)

    def get_id(self):
        return str(self.id)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(160), unique=True, nullable=False)
    slug = db.Column(db.String(180), unique=True, nullable=False)
    description = db.Column(db.Text)

class PostStatus:
    DRAFT = "draft"
    PUBLISHED = "published"
    APPROVED = "approved"
    DISAPPROVED = 'disapproved'

class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(220), nullable=False)
    slug = db.Column(db.String(240), unique=True, index=True)
    summary = db.Column(db.String(600))
    body = db.Column(db.Text)  # HTML sanitizado
    featured_image = db.Column(db.String(255))
    status = db.Column(db.String(20), default=PostStatus.DRAFT, index=True)
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'), nullable=False, index=True)
    author_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    published_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    category = db.relationship('Category', backref='posts')
    author = db.relationship('User', backref='posts')
    assets = db.relationship('PostAsset', backref='post', cascade='all, delete-orphan')

class AssetType:
    PDF = "pdf"
    VIDEO_LINK = "video_link"
    NEWS_LINK = "news_link"
    FILE = "file"
    IMAGE = "image"

class PostAsset(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'), nullable=False, index=True)
    asset_type = db.Column(db.String(20), nullable=False, index=True)
    title = db.Column(db.String(200))
    url = db.Column(db.String(1024))        # para links
    file_path = db.Column(db.String(1024))  # para uploads
    meta_json = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

   # post = db.relationship('Post', backref='assets')