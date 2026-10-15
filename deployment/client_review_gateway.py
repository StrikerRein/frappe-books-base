"""Public preview gateway: expose login and review endpoints, never the accounting app."""
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from urllib.parse import urlsplit,unquote
from urllib.request import Request,urlopen,HTTPRedirectHandler,build_opener
from urllib.error import HTTPError
import re

METHODS={'profile','list_reviews','find_transactions','assign','answer','review','overview','create_request','upload_document','download_document','approve_rule','preview_client'}
class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):return None
opener=build_opener(NoRedirect)
class Gateway(BaseHTTPRequestHandler):
    def log_message(self,*args):pass
    def do_GET(self):self.forward()
    def do_POST(self):self.forward()
    def do_HEAD(self):self.forward()
    def forward(self):
        path=unquote(urlsplit(self.path).path)
        if path=='/':
            self.send_response(302);self.send_header('Location','/client-review');self.end_headers();return
        permitted=path in {'/client-review','/login','/api/method/login','/api/method/logout'} or path.startswith('/assets/frappe/') or path in {'/api/method/frappe_books.review_portal.'+m for m in METHODS}
        if not permitted or '..' in path or '\\' in path:
            self.send_error(404,'Only the client review portal is available here.');return
        try:length=int(self.headers.get('Content-Length','0'))
        except ValueError:self.send_error(400);return
        maximum=12*1024*1024 if path=='/api/method/frappe_books.review_portal.upload_document' else 65536
        if length<0 or length>maximum:self.send_error(413);return
        headers={k:v for k,v in self.headers.items() if k.lower() not in {'host','connection','content-length','x-frappe-site-name','x-forwarded-proto','x-forwarded-host','x-forwarded-for','forwarded','accept-encoding'}}
        headers.update(Host='books.localhost',**{'X-Frappe-Site-Name':'books.localhost','X-Forwarded-Proto':'https','X-Forwarded-For':self.headers.get('CF-Connecting-IP','127.0.0.1'),'Accept-Encoding':'identity'})
        request=Request('http://127.0.0.1:8000'+self.path,data=self.rfile.read(length) if length else None,headers=headers,method=self.command)
        try:response=opener.open(request,timeout=40)
        except HTTPError as error:response=error
        except Exception:self.send_error(502,'Review service is temporarily unavailable.');return
        data=response.read()
        self.send_response(response.status)
        for name,value in response.headers.items():
            if name.lower() in {'connection','transfer-encoding','content-length','content-encoding'}:continue
            if name.lower()=='set-cookie':
                value=re.sub(r';\s*Domain=[^;]+','',value,flags=re.I)
                if not re.search(r';\s*secure(?:;|$)',value,re.I):value+='; Secure'
            if name.lower()=='location':
                value=re.sub(r'^https?://(?:books\.localhost|localhost|127\.0\.0\.1)(?::\d+)?','',value)
            self.send_header(name,value)
        self.send_header('Cache-Control','no-store')
        self.send_header('X-Robots-Tag','noindex, nofollow')
        self.send_header('X-Content-Type-Options','nosniff')
        self.send_header('Referrer-Policy','same-origin')
        self.send_header('Content-Length',str(len(data)))
        self.end_headers()
        if self.command!='HEAD':self.wfile.write(data)

ThreadingHTTPServer(('127.0.0.1',8090),Gateway).serve_forever()
