# ManaCache - TP Docker & CI/CD

![CI Docker Pipeline](https://github.com/OskarYnov/rendu-tp1-docker-oskar-morel/actions/workflows/ci.yml/badge.svg)

ManaCache est une application web 3-tiers (Reverse Proxy, Front-end, Back-end API) dédiée à la gestion d'une collection Magic: The Gathering. Le projet est entièrement conteneurisé avec Docker, orchestré avec Docker Swarm via une architecture multi-fichiers (overrides), doté d'un autoscaler personnalisé et validé par une pipeline CI/CD automatisée sous GitHub Actions.

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
| **Autoscaler** | `alpine:3.18` | Conteneur autonome avec `docker-cli` et `bash`, pilotant les réplicas Swarm en temps réel. Déployé uniquement en mode Swarm. | - |

---

## Organisation des Fichiers Compose et Overrides

Le projet utilise une séparation stricte entre environnement de développement et environnement de production en cluster :

- **`docker-compose.yml` (Fichier de base / Dev local) :**
  Définit les briques applicatives (`proxy`, `front`, `back`), leurs contextes de build, ports, volumes et variables d'environnement. Il utilise un réseau standard `bridge`, permettant de lancer le projet en local avec un simple `docker compose up -d` sans nécessiter l'activation préalable d'un cluster Swarm.

- **`swarm-stack.yml` (Fichier d'override Swarm / Production) :**
  Surcharge la configuration de base pour le déploiement en cluster. Il convertit le réseau `app-net` en mode `overlay`, applique les politiques de déploiement `deploy` (quotas CPU/RAM, réplicas, réservations CPU requises pour les métriques) et intègre le conteneur autonome d'**autoscaling**.

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

En mode Swarm, Docker ne compile pas les images à la volée. On build d'abord les images, puis on déploie en combinant le fichier de base et l'override :

```bash
# 1. Initialiser le mode Swarm (à faire une seule fois)
docker swarm init

# 2. Construire les images Docker
docker compose build
docker build -f Dockerfile.autoscaler -t autoscaler:latest .

# 3. Déployer la stack (Fichier de base + Override Swarm)
docker stack deploy -c docker-compose.yml -c swarm-stack.yml demo

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

### Option 2 : Déploiement classique Docker Compose (Dev local)

Idéal pour tester ou développer rapidement sans activer Swarm :

```bash
# Lancement en arrière-plan
docker compose up -d

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
- **Validation Compose et Overrides :** Validation syntaxique de `docker-compose.yml` seul, puis vérification de la fusion correcte de `docker-compose.yml` avec `swarm-stack.yml`.
- **ShellCheck :** Analyse statique du script shell `autoscale.sh`.
- **Ruff :** Vérification PEP8 et propreté du code Python `back/app.py`.

### 2. Build et Tests d'Intégration Réels
La CI ne se contente pas de vérifier la syntaxe, elle démarre réellement les conteneurs sur le runner :
1. **Build :** Construction de toutes les images applicatives.
2. **Up :** Démarrage de la stack via Docker Compose.
3. **Healthcheck :** Attente active de la disponibilité du Reverse Proxy sur le port 8080.
4. **Test Front :** Vérification de la présence de l'interface ManaCache (`GET /`).
5. **Test API :** Récupération de la collection initiale (`GET /api/cards`).
6. **Test Persistance :** Ajout d'une nouvelle carte via `POST /api/cards` et vérification immédiate que la donnée est bien conservée dans le volume partagé.
7. **Test Erreur 404 :** Vérification du comportement sur les routes non reconnues.

### 3. Test de Déploiement Swarm
- Initialisation d'un Swarm temporaire sur le runner GitHub Actions.
- Déploiement de la stack via la combinaison `docker stack deploy -c docker-compose.yml -c swarm-stack.yml demo`.
- Vérification de la convergence des 4 services (`proxy`, `front`, `back`, `autoscaler`) et validation de l'accès réseau.

---

## Bonnes Pratiques et Détails Techniques

- **Architecture Multi-Fichiers (Overrides) :** Découplage propre entre dev local (`docker-compose.yml`) et production clusterisée (`swarm-stack.yml`), évitant toute pollution Swarm en dev.
- **Sécurité (Utilisateur non-root) :** Le conteneur Python fonctionne avec l'utilisateur `appuser` (UID 1000). Les dossiers `/app/data` et `/app/images` sont pré-créés avec les bons droits (`chown`) pour éviter tout problème de permissions avec les volumes montés.
- **Arrêt gracieux (SIGTERM) :** Capture du signal `SIGTERM` dans `back/app.py` pour un arrêt propre (Code retour `0` au lieu d'un `SIGKILL` code 137).
- **Réseau Overlay Attachable :** Le réseau `app-net` dans Swarm est déclaré `attachable: true`, permettant aux conteneurs de diagnostic ou de debug de se connecter directement au réseau applicatif.
- **Portabilité UNIX ([`.gitattributes`](file:///d:/YNOV/DOCKER%20FULLSTACK/rendu-tp1-docker-oskar-morel/.gitattributes)) :** Forçage des sauts de ligne en `LF` pour éviter les erreurs d'interpréteur bash (`\r\n`) causées par Git sous Windows.
