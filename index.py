#!/usr/bin/env python3
import http.server
import base64
import os
import html
from urllib.parse import quote, urlparse, parse_qs
import posixpath

USERNAME = "basic_user"
PASSWORD = "basic_pass"
TOKEN = "basic_pass"  # shared token for Bearer or URL
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

    def do_POST(self):
        """Handle file uploads manually (no cgi module)."""
        if not self.is_authorized():
            self.do_AUTHHEAD()
            self.wfile.write(b'Authentication required or invalid credentials.')
            return

        content_type = self.headers.get('Content-Type')
        if not content_type or "multipart/form-data" not in content_type:
            self.send_error(400, "Bad request: expected multipart/form-data")
            return

        # Extract multipart boundary
        boundary = content_type.split("boundary=")[-1].strip()
        if not boundary:
            self.send_error(400, "No boundary found in Content-Type")
            return

        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length)

        boundary_bytes = b"--" + boundary.encode()
        parts = body.split(boundary_bytes)

        for part in parts:
            if b'Content-Disposition' not in part:
                continue

            # Separate headers and file data
            header_end = part.find(b"\r\n\r\n")
            if header_end == -1:
                continue

            headers = part[:header_end].decode(errors="ignore")
            content = part[header_end + 4 : -2]  # strip final CRLF

            # Extract filename from headers
            if 'filename="' not in headers:
                continue

            filename = headers.split('filename="')[1].split('"')[0]
            if not filename:
                continue

            filename = os.path.basename(filename)
            save_path = os.path.join(self.translate_path(self.path), filename)

            try:
                with open(save_path, "wb") as f:
                    f.write(content)

                self.send_response(200)
                self.send_header("Content-type", "text/html")
                self.end_headers()
                msg = f"<html><body><h3>File '{html.escape(filename)}' uploaded successfully.</h3><a href='{self.path}'>Back</a></body></html>"
                self.wfile.write(msg.encode("utf-8"))
                return
            except Exception as e:
                self.send_error(500, f"Error saving file: {e}")
                return

        self.send_error(400, "No valid file found in upload.")

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

        # Use only the path portion (drop any query)
        parsed = urlparse(self.path)
        request_path = parsed.path  # e.g. '/' or '/sub/dir'
        if not request_path.startswith('/'):
            request_path = '/' + request_path

        # ensure trailing slash for building relative paths
        request_base = request_path if request_path.endswith('/') else request_path + '/'

        enc = "utf-8"
        self.send_response(200)
        self.send_header("Content-type", f"text/html; charset={enc}")
        self.end_headers()

        # IMPORTANT: escape names when embedding in HTML. We'll pass raw names into data-name (escaped).
        html_parts = [
            "<!DOCTYPE html>",
            "<html><head>",
            "<meta charset='utf-8'>",
            "<title>File Server</title>",
            "<style>",
            "body { font-family: sans-serif; padding: 20px; }",
            "table { border-collapse: collapse; width: 100%; margin-top: 20px; }",
            "th, td { padding: 8px; border-bottom: 1px solid #ddd; }",
            "button { margin-left: 6px; padding: 4px 8px; cursor: pointer; }",
            "form { margin-top: 20px; }",
            "</style>",
            "</head><body>",
            f"<h2>Index of {html.escape(request_path)}</h2>",
            "<form method='POST' enctype='multipart/form-data'>"
            "<input type='file' name='file' required>"
            "<input type='submit' value='Upload File'>"
            "</form>",
            "<table>",
            "<tr><th>Name</th><th>Actions</th></tr>"
        ]
        safe_token = html.escape(TOKEN)
        safe_user = html.escape(USERNAME)
        safe_pass = html.escape(PASSWORD)
        # parent link
        if request_path != '/':
            parent = posixpath.dirname(request_path.rstrip('/'))
            if parent == '':
                parent = '/'
            parent_quoted = quote(parent)
            html_parts.append(
                f"<tr><td><a href='{html.escape(parent_quoted)}?token={safe_token}'>..</a></td><td></td></tr>"
            )

        # Expose server-side variables into JS for client-side command construction.
        # (NOTE: embedding secrets in HTML is risky — see note above.)
        

        for name in list_dir:
            fullname = os.path.join(path, name)
            is_dir = os.path.isdir(fullname)
            displayname = name + "/" if is_dir else name

            # Build the href (relative to current request path) properly so navigation works at any depth.
            # We will percent-encode each path-segment (here only 'name') to avoid encoding slashes.
            name_quoted = quote(name)
            if request_base == '/':
                href_path = '/' + name_quoted
            else:
                href_path = request_base + name_quoted

            if is_dir and not href_path.endswith('/'):
                href_path = href_path + '/'

            # Show the link to the file/directory, but do not include server token in href (we'll use JS to build full token URL)
            safe_display = html.escape(displayname)
            safe_name_attr = html.escape(name)  # for data-name attribute

            html_parts.append("<tr>")
            # link adds ?token=... only for files when clicked (we still include basic href so navigation works)
            html_parts.append(f"<td><a href='{html.escape(href_path)}?token={safe_token}'>{safe_display}</a></td>")

            if is_dir:
                html_parts.append("<td></td>")
            else:
                # Provide buttons that have data-* attributes; JS will build commands using window.location.origin + current pathname
                html_parts.append(
                    "<td>"
                    f"<button class='copy-wget' data-name='{safe_name_attr}'>Copy wget</button>"
                    f"<button class='copy-curl' data-name='{safe_name_attr}'>Copy curl</button>"
                    f"<button class='copy-token-url' data-name='{safe_name_attr}'>Copy ?token URL</button>"
                    "</td>"
                )
            html_parts.append("</tr>")

        html_parts.extend([
            "</table>",
            "<script>",
            # Inject server-side token and credentials for client-side command assembly (be careful: security risk).
            f"const SERVER_TOKEN = '{safe_token}';",
            f"const SERVER_USER = '{safe_user}';",
            f"const SERVER_PASS = '{safe_pass}';",
            "",
            "function fallbackCopyText(text) {",
            "  const ta = document.createElement('textarea');",
            "  ta.value = text;",
            "  document.body.appendChild(ta);",
            "  ta.select();",
            "  try { document.execCommand('copy'); alert('Copied: ' + text); }",
            "  catch (e) { alert('Copy failed — please select and copy manually: ' + text); }",
            "  document.body.removeChild(ta);",
            "}",
            "",
            "function copyText(text) {",
            "  if (navigator && navigator.clipboard && navigator.clipboard.writeText) {",
            "    navigator.clipboard.writeText(text).then(()=>{ alert('Copied: ' + text); }, ()=>{ fallbackCopyText(text); });",
            "  } else {",
            "    fallbackCopyText(text);",
            "  }",
            "}",
            "",
            "// Build absolute URL for a file name relative to the current browser path",
            "function buildFileUrl(name, isDir) {",
            "  let base = window.location.pathname;",
            "  if (!base.endsWith('/')) base = base + '/';",
            "  // encodeURIComponent for single path segment",
            "  const seg = encodeURIComponent(name);",
            "  return window.location.origin + (base === '//' ? '/' : base) + seg + (isDir ? '/' : '');",
            "}",
            "",
            "document.addEventListener('DOMContentLoaded', function(){",
            "  // copy wget buttons",
            "  document.querySelectorAll('.copy-wget').forEach(btn => {",
            "    btn.addEventListener('click', function(){",
            "      const name = this.getAttribute('data-name');",
            "      const fileUrl = buildFileUrl(name, false);",
            "      const cmd = `wget --user=${SERVER_USER} --password=${SERVER_PASS} \"${fileUrl}\"`;",
            "      copyText(cmd);",
            "    });",
            "  });",
            "",
            "  // copy curl buttons",
            "  document.querySelectorAll('.copy-curl').forEach(btn => {",
            "    btn.addEventListener('click', function(){",
            "      const name = this.getAttribute('data-name');",
            "      const fileUrl = buildFileUrl(name, false);",
            "      const cmd = `curl -u ${SERVER_USER}:${SERVER_PASS} -O \"${fileUrl}\"`;",
            "      copyText(cmd);",
            "    });",
            "  });",
            "",
            "  // copy token-url buttons (build from window.location so host/origin is current browser host)",
            "  document.querySelectorAll('.copy-token-url').forEach(btn => {",
            "    btn.addEventListener('click', function(){",
            "      const name = this.getAttribute('data-name');",
            "      const fileUrl = buildFileUrl(name, false);",
            "      const tokenUrl = `${fileUrl}?token=${SERVER_TOKEN}`;",
            "      copyText(tokenUrl);",
            "    });",
            "  });",
            "});",
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
    http.server.test(HandlerClass=AuthHandler, port=PORT, bind='0.0.0.0')
