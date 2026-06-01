import os
import re
import unicodedata
import bleach

# Tenta importar o CSSSanitizer (Necessário para versões novas do Bleach > 5.0)
try:
    from bleach.css_sanitizer import CSSSanitizer
except ImportError:
    CSSSanitizer = None

ALLOWED_EXTENSIONS = {"pdf", "png", "jpg", "jpeg", "gif", "mp4", "webp"}
ALLOWED_MIMES = {
    "application/pdf",
    "image/png", "image/jpeg", "image/gif", "image/webp",
    "video/mp4"
}

def ensure_upload_folder(path: str):
    os.makedirs(path, exist_ok=True)

def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

def strip_tags(html: str) -> str:
    """Remove todo HTML para gerar o resumo limpo."""
    return bleach.clean(html or "", tags=[], strip=True)

def sanitize_html(html: str) -> str:
    """
    CONFIGURAÇÃO 'WYSIWYG REAL' (What You See Is What You Get).
    Permite praticamente TUDO para garantir que layouts complexos copiados
    de outros sites (G1, CNN, etc) sejam renderizados perfeitamente.
    Usa função callable para suportar data-* e aria-* corretamente.
    """
    if not html:
        return ""

    # Permite todas as tags possíveis encontradas em sites modernos
    allowed_tags = bleach.sanitizer.ALLOWED_TAGS.union({
        # Layout e Estrutura
        'div', 'span', 'p', 'br', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'hr',
        'section', 'article', 'header', 'footer', 'nav', 'main', 'aside',
        'figure', 'figcaption', 'details', 'summary', 'dialog',

        # Listas e Tabelas
        'ul', 'ol', 'li', 'dl', 'dt', 'dd',
        'table', 'thead', 'tbody', 'tfoot', 'tr', 'td', 'th', 'col', 'colgroup', 'caption',

        # Formatação de Texto
        'strong', 'em', 'b', 'i', 'u', 's', 'small', 'sub', 'sup', 'mark', 'time',
        'code', 'pre', 'blockquote', 'q', 'cite', 'abbr', 'address', 'kbd', 'var', 'samp',

        # Mídia e Embeds
        'img', 'video', 'audio', 'source', 'iframe', 'embed', 'object', 'param', 'picture', 'track',

        # SVG e Gráficos (Essencial para ícones e logos)
        'svg', 'path', 'g', 'circle', 'rect', 'line', 'polyline', 'polygon',
        'text', 'defs', 'symbol', 'use', 'clippath', 'mask', 'pattern',
        'lineargradient', 'radialgradient', 'stop', 'image', 'marker',

        # Interatividade e Estilo
        'style', 'button', 'a', 'label', 'input'
    })

    # Atributos específicos por tag (sem wildcards)
    _tag_specific_attrs = {
        'a': {'href', 'name', 'download', 'hreflang', 'type'},
        'img': {'src', 'alt', 'srcset', 'sizes', 'loading', 'decoding', 'crossorigin', 'usemap', 'ismap'},
        'iframe': {'src', 'frameborder', 'allowfullscreen', 'allow', 'scrolling', 'sandbox', 'loading', 'referrerpolicy'},
        'video': {'src', 'controls', 'poster', 'autoplay', 'muted', 'loop', 'playsinline', 'preload', 'crossorigin'},
        'audio': {'src', 'controls', 'autoplay', 'muted', 'loop', 'preload'},
        'source': {'src', 'type', 'media', 'srcset', 'sizes'},
        'time': {'datetime'},
        'button': {'type', 'disabled', 'name', 'value'},
        'input': {'type', 'checked', 'disabled', 'name', 'value', 'placeholder', 'readonly'},
        # Atributos SVG
        'svg': {'viewbox', 'xmlns', 'preserveaspectratio', 'fill', 'stroke', 'version', 'x', 'y'},
        'path': {'d', 'fill', 'stroke', 'stroke-width', 'opacity', 'fill-rule', 'clip-rule',
                 'stroke-linecap', 'stroke-linejoin', 'stroke-miterlimit', 'stroke-dasharray', 'stroke-dashoffset'},
        'rect': {'x', 'y', 'rx', 'ry', 'fill', 'stroke'},
        'circle': {'cx', 'cy', 'r', 'fill', 'stroke'},
        'line': {'x1', 'y1', 'x2', 'y2', 'stroke', 'stroke-width'},
        'g': {'transform', 'fill', 'stroke', 'opacity'},
        'use': {'href', 'xlink:href'},
        'stop': {'offset', 'stop-color', 'stop-opacity'},
    }

    # Atributos globais permitidos para TODAS as tags
    _global_attrs = {
        'class', 'style', 'id', 'title', 'align', 'width', 'height',
        'dir', 'lang', 'tabindex', 'target', 'rel', 'role',
        'hidden', 'draggable', 'spellcheck',
    }

    def allow_attrs(tag, name, value):
        """
        Função callable para bleach.
        Permite atributos globais, data-*, aria-* e atributos específicos por tag.
        """
        # Permite data-* e aria-* em qualquer tag (suporte a Bootstrap, etc.)
        if name.startswith('data-') or name.startswith('aria-'):
            return True
        # Permite atributos globais
        if name in _global_attrs:
            return True
        # Permite atributos específicos da tag
        if name in _tag_specific_attrs.get(tag, set()):
            return True
        return False

    # LISTA DE ESTILOS CSS PERMITIDOS
    allowed_styles = [
        'color', 'background-color', 'font-family', 'font-size', 'font-weight',
        'text-align', 'text-decoration', 'text-transform', 'line-height', 'letter-spacing',
        'width', 'height', 'max-width', 'min-width', 'max-height', 'min-height',
        'margin', 'margin-top', 'margin-bottom', 'margin-left', 'margin-right',
        'padding', 'padding-top', 'padding-bottom', 'padding-left', 'padding-right',
        'border', 'border-top', 'border-bottom', 'border-left', 'border-right',
        'border-radius', 'border-collapse', 'border-spacing', 'border-color', 'border-style', 'border-width',
        'display', 'float', 'overflow', 'vertical-align', 'list-style-type', 'background',
        'position', 'top', 'left', 'right', 'bottom', 'z-index',
        'flex', 'flex-direction', 'flex-wrap', 'justify-content', 'align-items',
        'gap', 'grid', 'grid-template-columns', 'grid-template-rows',
        'opacity', 'transform', 'transition', 'cursor', 'pointer-events',
        'object-fit', 'object-position',
    ]

    # Prepara os argumentos padrão
    clean_kwargs = {
        'tags': allowed_tags,
        'attributes': allow_attrs,   # <-- callable em vez de dict
        'protocols': ['http', 'https', 'mailto', 'data', 'tel', 'ftp'],
        'strip': False,
    }

   # Bleach 6.x: sempre usa CSSSanitizer, nunca passa 'styles='  
    if CSSSanitizer:  
        clean_kwargs['css_sanitizer'] = CSSSanitizer(allowed_css_properties=allowed_styles)  
    # Bleach < 5.0 (sem CSSSanitizer): passa styles diretamente  
    # Nota: bleach 6.x não suporta styles=, então só usamos se CSSSanitizer não existir  
    # e a versão for realmente antiga (< 5.0)  
    elif bleach.__version__ < '5':  
        clean_kwargs['styles'] = allowed_styles  
  
    return bleach.clean(html, **clean_kwargs)


def slugify(value: str) -> str:
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    value = re.sub(r"[^a-zA-Z0-9\- ]+", "", value).strip().lower()
    value = re.sub(r"[\s\-]+", "-", value)
    return value