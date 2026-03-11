import io
from django.http import HttpResponse
from django.template.loader import get_template
from xhtml2pdf import pisa
from django.conf import settings
import os

def render_to_pdf(template_src, context_dict={}):
    template = get_template(template_src)
    html = template.render(context_dict)
    result = io.BytesIO()
    
    # Função para resolver caminhos de recursos (CSS, imagens) para o pisa
    def link_callback(uri, rel):
        from django.contrib.staticfiles import finders
        result = finders.find(uri)
        if result:
            if not isinstance(result, (list, tuple)):
                result = [result]
            path = result[0]
        else:
            s_url = settings.STATIC_URL
            s_root = settings.STATIC_ROOT
            m_url = settings.MEDIA_URL
            m_root = settings.MEDIA_ROOT

            if uri.startswith(m_url):
                path = os.path.join(m_root, uri.replace(m_url, ""))
            elif uri.startswith(s_url):
                path = os.path.join(s_root, uri.replace(s_url, ""))
            else:
                return uri

        # Garantir que o arquivo exista
        if not os.path.isfile(path):
            print(f"pdf_utils error: File not found {path}")
            return uri
            
        return path

    pdf = pisa.pisaDocument(io.BytesIO(html.encode("UTF-8")), result, link_callback=link_callback)
    
    if not pdf.err:
        return HttpResponse(result.getvalue(), content_type='application/pdf')
    return None
