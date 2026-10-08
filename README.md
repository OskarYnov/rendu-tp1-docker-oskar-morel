# Projet TP Docker - Cloud Personnel Virtuel (ManaCache)

## Présentation du Projet

Ce projet consiste à concevoir une application web modulaire nommée **ManaCache** (gestionnaire de collection Magic: The Gathering) basée sur Docker et Docker Compose. L'architecture repose sur trois types de conteneurs personnalisés, sans utiliser d'images pré-configurées complexes du Docker Hub.

### Schéma de l'Architecture

```text
                 [ Réseau Externe / Hôte ]
                            │
                       Port 8080
                            │
               ┌────────────▼─────────────┐
               │                          │
               │   Reverse Proxy (Nginx)  │
               │    (Routage & Sécurité)  │
               │                          │
               └──────┬────────────┬──────┘
                      │            │
             /--------/            \--------\  [ Réseau Interne Isolé : app-net ]
             │                              │
      Requêtes vers /                Requêtes vers /api
             │                              │
    ┌────────▼────────┐            ┌────────▼────────┐
    │                 │            │                 │
    │  Front (Nginx)  │            │  Back (Python)  │
    │  (Fichiers UI)  │            │  (Logique API)  │
    │                 │            │                 │
    └─────────────────┘            └────────┬────────┘
                                            │
                                  /---------┴---------\
                                  │                   │
                        ┌─────────▼────────┐ ┌────────▼─────────┐
                        │ Volume mtg_data  │ │Volume mtg_images │
                        │  (JSON / SQLite) │ │ (Cache des scans)│
                        └──────────────────┘ └──────────────────┘
```

---

## 1. Choix de Build et Personnalisation des Images

### A. Le Reverse Proxy (`/proxy`)
- **Image de base :** `nginx:alpine` pour sa légèreté, sa rapidité et sa sécurité (surface d'attaque réduite).
- **Opérations OS :** Mise à jour des paquets `apk`, installation de `curl` pour les tests de santé, et nettoyage du cache.
- **Configuration :** Suppression du fichier par défaut et intégration d'un `nginx.conf` personnalisé. Il route le trafic racine (`/`) vers le front et le trafic `/api` vers le back.
- **Ports ouverts :** Port `80` en interne.

### B. Le Front-End (`/front`)
- **Image de base :** `nginx:alpine`.
- **Opérations OS :** Installation de `curl` et nettoyage du cache.
- **Configuration :** Intégration de l'interface `index.html` (Vanilla JS interagissant avec l'API) et application de permissions strictes (`chown` et `chmod`).
- **Ports ouverts :** Port `80` en interne.

### C. Le Back-End (`/back`)
- **Image de base :** `python:3.11-slim`.
- **Sécurité et Permissions :** Création d'un utilisateur non-root (`appuser`). Création préalable des dossiers `/app/data` et `/app/images` avec les bons droits (`chown`) pour éviter les conflits de permissions avec les volumes Docker.
- **Stabilité :** Interception des signaux `SIGTERM` dans le code Python pour garantir un arrêt propre (Exit Code `0` au lieu de `137`).
- **Ports ouverts :** Port `5000` en interne.

---

## 2. Orchestration, Réseaux et Volumes (docker-compose.yml)

### Variables d'Environnement (`.env`)
L'infrastructure est paramétrable via un fichier `.env` à la racine, injecté dynamiquement au *runtime* (ex: `PROXY