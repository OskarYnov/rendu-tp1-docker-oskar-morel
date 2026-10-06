from http.server import HTTPServer, BaseHTTPRequestHandler

class SimpleHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "application/json")
        self.end_headers()
        self.wfile.write(b'{"status": "success", "message": "Hello depuis le Backend de mon Cloud Docker !"}')

if __name__ == "__main__":
    server = HTTPServer(("0.0.0.0", 5000), SimpleHandler)
    print("Backend lance sur le port 5000...")
    server.serve_forever()