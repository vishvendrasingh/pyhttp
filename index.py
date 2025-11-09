#!/usr/bin/env python3
import http.server
import base64
import os
import html
from urllib.parse import quote, urlparse, parse_qs

USERNAME = "admin"
PASSWORD = "admin"
TOKEN = "admin"  # shared token for Bearer or URL
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
        if self.is_authorized():
            return self.list_or_serve()
        else:
            self.do_AUTHHEAD()
            self.wfile.write(b'Authentication required or invalid credentials.')

    def is_authorized(self):
        """Check for Basic, Bearer, or URL token authorization."""
        # --- 1. Check for Basic Auth ---
        auth_header = self.headers.get('Authorization')
        expected_basic = "Basic " + base64.b64encode(f"{USERNAME}:{PASSWORD}".encode()).decode()

        if auth_header == expected_basic:
            return True

        # --- 2. Check for Bearer Token ---
        if auth_header and auth_header.strip() == f"Bearer {TOKEN}":
            return True

        # --- 3. Check for URL token ---
        query = parse_qs(urlparse(self.path).query)
        if 'token' in query and query['token'][0] == TOKEN:
            return True

        return False

    def list_or_serve(self):
        """Serve files or directory listing with copy buttons."""
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
            token_url = f"{file_url}?token={TOKEN}"
            # bearer_cmd = f"curl -H 'Authorization: Bearer {TOKEN}' -O \"{file_url}\""

            html_parts.append("<tr>")
            html_parts.append(f"<td><a href='{linkname}'>{displayname}</a></td>")

            if os.path.isdir(fullname):
                html_parts.append("<td></td>")
            else:
                html_parts.append(
                    "<td>"
                    f"<button onclick=\"copyToClipboard('{html.escape(wget_cmd)}')\">Copy wget</button>"
                    f"<button onclick=\"copyToClipboard('{html.escape(curl_cmd)}')\">Copy curl</button>"
                    # f"<button onclick=\"copyToClipboard('{html.escape(bearer_cmd)}')\">Copy Bearer</button>"
                    f"<button onclick=\"copyToClipboard('{html.escape(token_url)}')\">Copy ?token URL</button>"
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
    print(f"Serving on port {PORT} with authentication:")
    print(f"- Basic: {USERNAME}/{PASSWORD}")
    print(f"- Bearer token: {TOKEN}")
    print(f"- URL token: ?token={TOKEN}")
    http.server.test(HandlerClass=AuthHandler, port=PORT)
