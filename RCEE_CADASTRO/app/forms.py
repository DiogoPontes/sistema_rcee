from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, TextAreaField, SelectField, FileField, HiddenField, DateTimeLocalField
from wtforms.validators import DataRequired, Length, Optional, Regexp
from flask_wtf.file import FileField, FileAllowed

class LoginForm(FlaskForm):
    email = StringField("Email", validators=[
        DataRequired(),
        Regexp(r'^[^@]+@[^@]+\.[^@]+$', message="Email inválido.")
    ])
    password = PasswordField("Senha", validators=[DataRequired()])

class PostForm(FlaskForm):
    title = StringField("Título", validators=[DataRequired(), Length(max=220)])
    slug = StringField("Slug", validators=[Optional(), Length(max=240)])
    summary = TextAreaField("Resumo", validators=[Optional()])
    body_html = HiddenField("BodyHTML")  # recebe HTML sanitizado do Quill
    category_id = SelectField("Categoria", coerce=int, validators=[DataRequired()])
    status = SelectField("Status", choices=[("draft", "Rascunho"), ("published", "Publicado")], validators=[DataRequired()])

    # ADICIONADO 'webp' AQUI NA LISTA PERMITIDA
    featured_image = FileField('Imagem de Destaque', validators=[
        FileAllowed(['jpg', 'jpeg', 'png', 'gif', 'webp'], 'Apenas imagens (JPG, PNG, GIF, WEBP) são permitidas!')
    ])

    published_at = DateTimeLocalField(  
        "Data de Publicação",  
        format="%Y-%m-%dT%H:%M",  
        validators=[DataRequired(message="A data de publicação é obrigatória.")],  
        default=None  
    )

class AssetLinkForm(FlaskForm):
    title = StringField("Título", validators=[Optional(), Length(max=200)])
    url = StringField("URL", validators=[DataRequired(), Length(max=1024)])
    asset_type = SelectField("Tipo", choices=[("video_link","Vídeo"), ("news_link","Notícia")], validators=[DataRequired()])

class AssetUploadForm(FlaskForm):
    title = StringField("Título", validators=[Optional(), Length(max=200)])
    file = FileField("Arquivo")  # validação no handler