#!/usr/bin/env python3
import http.server
import base64
import os
import html   
from urllib.parse import quote

USERNAME = "basic_user"
PASSWORD = "basic_pass"
PORT = 8234


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
                return self.list_or_serve()
            else:
                self.do_AUTHHEAD()
                self.wfile.write(b'Invalid credentials.')

    def list_or_serve(self):
        """Serve files or directory listing with copy buttons"""
        path = self.translate_path(self.path)
        if os.path.isdir(path):
            return self.list_directory(path)
        return http.server.SimpleHTTPRequestHandler.do_GET(self)

    def list_directory(self, path):
        try:
            list_dir = os.listdir(path)
        except OSError:
            self.send_error(404, "No permission to list directory")
            return None

        list_dir.sort(key=lambda a: a.lower())
        display_path = quote(self.path)
        enc = "utf-8"
        self.send_response(200)
        self.send_header("Content-type", f"text/html; charset={enc}")
        self.end_headers()

        # ✅ renamed from html → html_parts
        html_parts = [
            "<!DOCTYPE html>",
            "<html><head>",
            "<meta charset='utf-8'>",
            "<title>File Server</title>",
            "<style>",
            "body { font-family: sans-serif; padding: 20px; }",
            "table { border-collapse: collapse; width: 100%; }",
            "th, td { padding: 8px; border-bottom: 1px solid #ddd; }",
            "button { margin-left: 10px; padding: 3px 6px; cursor: pointer; }",
            "</style>",
            "</head><body>",
            f"<h2>Index of {display_path}</h2>",
            "<table>",
            "<tr><th>Name</th><th>Actions</th></tr>"
        ]

        if self.path != '/':
            parent = os.path.dirname(self.path.rstrip('/'))
            html_parts.append(f"<tr><td><a href='{quote(parent) or '/'}'>..</a></td><td></td></tr>")

        for name in list_dir:
            fullname = os.path.join(path, name)
            displayname = name + "/" if os.path.isdir(fullname) else name
            linkname = quote(name)
            file_url = f"http://{self.headers.get('Host')}{self.path.rstrip('/')}/{linkname}"

            wget_cmd = f"wget --user={USERNAME} --password={PASSWORD} \"{file_url}\""
            curl_cmd = f"curl -u {USERNAME}:{PASSWORD} -O \"{file_url}\""

            wget_escaped = html.escape(wget_cmd)
            curl_escaped = html.escape(curl_cmd)

            wget_safe = wget_escaped.replace("'", "\\'")
            curl_safe = curl_escaped.replace("'", "\\'")
            
            html_parts.append("<tr>")
            html_parts.append(f"<td><a href='{linkname}'>{displayname}</a></td>")

            if os.path.isdir(fullname):
                html_parts.append("<td></td>")
            else:
                html_parts.append(
                    "<td>"
                    f"<button onclick=\"copyToClipboard('{wget_safe}')\">Copy wget</button>"
                    f"<button onclick=\"copyToClipboard('{curl_safe}')\">Copy curl</button>"
                    "</td>"
                )
            html_parts.append("</tr>")

        html_parts.extend([
            "</table>",
            "<script>",
            "function copyToClipboard(text) { navigator.clipboard.writeText(text); alert('Copied: ' + text); }",
            "</script>",
            "</body></html>"
        ])

        self.wfile.write("\n".join(html_parts).encode(enc))
        return None


if __name__ == '__main__':
    print(f"Serving on port {PORT} with basic auth ({USERNAME}/{PASSWORD})...")
    http.server.test(HandlerClass=AuthHandler, port=PORT)
