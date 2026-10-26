# ManaCache - TP Docker & CI/CD

![CI Docker Pipeline](https://github.com/OskarYnov/rendu-tp1-docker-oskar-morel/actions/workflows/ci.yml/badge.svg)

**ManaCache** est une application web 3-tiers (Reverse Proxy, Front-end, Back-end API) dédiée à la gestion d'une collection Magic: The Gathering. Le projet est entièrement conteneurisé avec Docker, orchestré avec Docker Swarm, doté d'un autoscaler personnalisé et validé par une pipeline CI/CD automatisée sous GitHub Actions.

---

## Architecture du Projet

```text
                 [ Machine Hôte ]
                        │
                    Port 8080
                        │
           ┌────────────▼────────────┐
           │   Reverse Proxy (Nginx) │
           │   (Routage & Sécurité)  │
           └──────┬───────────┬──────┘
                  │           │
         /--------/           \--------\  [ Réseau isolé : app-net ]
         │                             │
    Requêtes vers /               Requêtes vers /api
         │                             │
┌────────▼────────┐           ┌────────▼────────┐
│  Front (Nginx)  │           │  Back (Python)  │
│  (Interface UI) │           │  (Logique API)  │
└─────────────────┘           └────────┬────────┘
                                       │
                             /---------┴---------\
                             │                   │
                   ┌─────────▼────────┐ ┌────────▼─────────┐
                   │ Volume mtg_data  │ │Volume mtg_images │
                   │  (JSON / SQLite) │ │ (Cache visuels)  │
                   └──────────────────┘ └──────────────────┘
```

---

## Les Services

| Service | Image de base | Rôle & Particularités | Port interne |
| :--- | :--- | :--- | :--- |
| **Proxy** | `nginx:alpine` | Point d'entrée unique. Route `/` vers le Front et `/api` vers le Back. Sécurisé et allégé. | `80` |
| **Front** | `nginx:alpine` | Sert l'interface web statique (HTML / JS Vanilla) avec permissions strictes. | `80` |
| **Back** | `python:3.11-slim` | API REST de gestion des cartes. Tourne sous utilisateur non-root (`appuser`), arrêt propre via signal `SIGTERM`. | `5000` |
| **Autoscaler** | `alpine:3.18` | Conteneur autonome avec `docker-cli` et `bash`, pilotant les réplicas Swarm en temps réel. | - |

---

## Autoscaling (Mode Swarm)

Le service critique (`back`) est monitoré et scalé dynamiquement par le conteneur [`autoscale.sh`](file:///d:/YNOV/DOCKER%20FULLSTACK/rendu-tp1-docker-oskar-morel/autoscale.sh) :
- **Métrique analysée :** Utilisation CPU moyenne cumulée du service `back`.
- **Scale UP (+1 réplica) :** Déclenché si la charge CPU dépasse **80%** (plafond max : 5 réplicas).
- **Scale DOWN (-1 réplica) :** Déclenché si la charge redescend sous **10%** (seuil min : 1 réplica).
- **Placement :** Déployé en mode `global` avec contrainte `node.role == manager` et montage du socket `/var/run/docker.sock`.

---

## Démarrage Rapide

### Configuration (.env)
Un fichier `.env` est présent à la racine pour paramétrer l'environnement :
```env
PROXY_PORT=8080
PROXY_MODE=production
APP_ENV=production
STORAGE_TYPE=sqlite
```

---

### Option 1 : Déploiement en Mode Swarm (Recommandé)

En mode Swarm, Docker ne compile pas les images à la volée. On build d'abord en local, puis on déploie la stack :

```bash
# 1. Initialiser le mode Swarm (à faire une seule fois)
docker swarm init

# 2. Construire les images Docker
docker compose build

# 3. Déployer la stack complète
docker stack deploy -c docker-compose.yml demo

# 4. Vérifier que tous les services sont bien démarrés (1/1)
docker stack services demo
docker service ps demo_back demo_front demo_proxy demo_autoscaler

# 5. Tester l'application
# Interface web : http://localhost:8080/
# API directe   : http://localhost:8080/api/cards

# 6. Arrêter la stack
docker stack rm demo
```

---

### Option 2 : Déploiement classique Docker Compose

Idéal pour tester rapidement sans activer Swarm :

```bash
# Lancement en arrière-plan
docker compose up -d proxy front back

# Suivre les logs en direct
docker compose logs -f

# Arrêter les conteneurs et supprimer les volumes
docker compose down -v
```

---

## Pipeline CI/CD (GitHub Actions)

À chaque `push` ou `pull_request`, la pipeline ([`.github/workflows/ci.yml`](file:///d:/YNOV/DOCKER%20FULLSTACK/rendu-tp1-docker-oskar-morel/.github/workflows/ci.yml)) exécute automatiquement 3 jobs :

### 1. Linting et Qualité du Code
- **Hadolint :** Analyse statique de tous les Dockerfiles (`back/dockerfile`, `front/dockerfile`, `proxy/dockerfile`, `Dockerfile.autoscaler`).
- **Docker Compose Config :** Validation syntaxique et cohérence de `docker-compose.yml` et de l'override `swarm-stack.yml`.
- **ShellCheck :** Analyse statique du script shell `autoscale.sh`.
- **Ruff :** Vérification PEP8 et propreté du code Python `back/app.py`.

### 2. Build et Tests d'Intégration Réels
La CI ne se contente pas de vérifier la syntaxe, elle démarre réellement les conteneurs sur le runner :
1. **Build :** Construction de toutes les images.
2. **Up :** Démarrage des conteneurs via Docker Compose.
3. **Healthcheck :** Attente active de la disponibilité du Reverse Proxy.
4. **Test Front :** Vérification de la présence de l'interface ManaCache (`GET /`).
5. **Test API :** Récupération de la collection initiale (`GET /api/cards`).
6. **Test Persistance :** Ajout d'une nouvelle carte via `POST /api/cards` et vérification immédiate que la donnée est bien conservée dans le volume partagé.
7. **Test Erreur 404 :** Vérification du comportement sur les routes non reconnues.

### 3. Test de Déploiement Swarm
- Initialisation d'un Swarm temporaire sur le runner GitHub Actions.
- Déploiement de la stack et vérification de la convergence des 4 services.

---

## Bonnes Pratiques et Détails Techniques

- **Sécurité (Utilisateur non-root) :** Le conteneur Python fonctionne avec l'utilisateur `appuser` (UID 1000). Les dossiers `/app/data` et `/app/images` sont pré-créés avec les bons droits (`chown`) pour éviter tout problème de permissions avec les volumes montés.
- **Arrêt gracieux (SIGTERM) :** Capture du signal `SIGTERM` dans `back/app.py` pour un arrêt propre (Code retour `0` au lieu d'un `SIGKILL` code 137).
- **Interopérabilité Réseau (attachable: true) :** Le réseau overlay `app-net` est marqué comme `attachable`, ce qui permet d'utiliser indifféremment `docker compose up` ou `docker stack deploy` sans conflit.
- **Portabilité UNIX ([`.gitattributes`](file:///d:/YNOV/DOCKER%20FULLSTACK/rendu-tp1-docker-oskar-morel/.gitattributes)) :** Forçage des sauts de ligne en `LF` pour éviter les erreurs d'interpréteur bash (`\r\n`) causées par Git sous Windows.
