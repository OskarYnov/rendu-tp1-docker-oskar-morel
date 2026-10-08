import json
import os
import signal
import sys
from http.server import HTTPServer, BaseHTTPRequestHandler

DATA_FILE = "/app/data/collection.json"

# Arrêt propre du conteneur (Code 0 au lieu de 137)
def handle_exit(signum, frame):
    sys.exit(0)
signal.signal(signal.SIGTERM, handle_exit)

# Initialisation du volume avec une carte par défaut si le fichier n'existe pas
os.makedirs("/app/data", exist_ok=True)
if not os.path.exists(DATA_FILE):
    with open(DATA_FILE, "w") as f:
        json.dump([{"name": "Black Lotus", "edition": "Alpha"}], f)

class MTGHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/api/cards':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            
            # Lecture depuis le volume
            with open(DATA_FILE, 'r') as f:
                data = f.read()
            self.wfile.write(data.encode('utf-8'))
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        if self.path == '/api/cards':
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length)
            new_card = json.loads(post_data.decode('utf-8'))

            # Lecture de l'existant
            with open(DATA_FILE, 'r') as f:
                cards = json.load(f)

            # Ajout de la nouvelle carte et sauvegarde dans le volume
            cards.append(new_card)
            with open(DATA_FILE, 'w') as f:
                json.dump(cards, f)

            self.send_response(201)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"status": "success", "card": new_card}).encode('utf-8'))

if __name__ == "__main__":
    server = HTTPServer(("0.0.0.0", 5000), MTGHandler)
    print("API ManaCache lancée sur le port 5000...")
    server.serve_forever()