#!/usr/bin/env python3
import http.server
import base64

USERNAME = "basic_user"
PASSWORD = "basic_pass"

class AuthHandler(http.server.SimpleHTTPRequestHandler):
    def do_HEAD(self):
        return self.do_GET()

    def do_AUTHHEAD(self):
        self.send_response(401)
        self.send_header('WWW-Authenticate', 'Basic realm="Auth required"')
        self.send_header('Content-type', 'text/html')
        self.end_headers()

    def do_GET(self):
        auth_header = self.headers.get('Authorization')
        if auth_header is None:
            self.do_AUTHHEAD()
            self.wfile.write(b'Authentication required.')
        else:
            encoded = base64.b64encode(f"{USERNAME}:{PASSWORD}".encode()).decode()
            if auth_header == f"Basic {encoded}":
                return http.server.SimpleHTTPRequestHandler.do_GET(self)
            else:
                self.do_AUTHHEAD()
                self.wfile.write(b'Invalid credentials.')

if __name__ == '__main__':
    http.server.test(HandlerClass=AuthHandler, port=8234)
