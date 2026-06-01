import os
import re
import unicodedata
import bleach

ALLOWED_EXTENSIONS = {"pdf", "png", "jpg", "jpeg", "gif", "mp4"}
ALLOWED_MIMES = {
    "application/pdf",
    "image/png", "image/jpeg", "image/gif",
    "video/mp4"
}

def ensure_upload_folder(path: str):
    os.makedirs(path, exist_ok=True)

def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

def sanitize_html(html: str) -> str:
    tags = bleach.sanitizer.ALLOWED_TAGS.union({"p","br","strong","em","u","ul","ol","li","blockquote","h1","h2","h3","h4","h5","h6","a","img","code","pre"})
    attrs = {**bleach.sanitizer.ALLOWED_ATTRIBUTES, "a": ["href","title","target","rel"], "img": ["src","alt","title"]}
    return bleach.clean(html or "", tags=tags, attributes=attrs, strip=True)

def slugify(value: str) -> str:
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    value = re.sub(r"[^a-zA-Z0-9\- ]+", "", value).strip().lower()
    value = re.sub(r"[\s\-]+", "-", value)
    return value