import os
from dotenv import load_dotenv
load_dotenv()

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-change-me")
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", "mysql+pymysql://root:alfa0101@10.1.140.15/rcee_admin_bkp")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = os.getenv("UPLOAD_FOLDER", os.path.join(os.path.dirname(__file__), "app", "static", "uploads"))
    MAX_CONTENT_LENGTH = int(os.getenv("MAX_CONTENT_LENGTH", 700 * 1024 * 1024))  # 70MB
    WTF_CSRF_ENABLED = True

class DevConfig(Config):
    DEBUG = True

config = {
    "default": DevConfig,
    "development": DevConfig
}