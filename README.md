# Projet TP Docker - Cloud Personnel Virtuel
## Presentation du Projet

Ce projet consiste a concevoir une application web modulaire nommee **ManaCache** (gestionnaire de collection Magic: The Gathering) basee sur Docker et Docker Compose. L'architecture repose sur trois types de conteneurs personnalises :

1. Un Reverse Proxy Nginx pour router le trafic (exposé sur le port 8080).
2. Un Front-End Nginx pour l'interface web statique.
3. Un Back-End Python pour l'API et la gestion des données persistes.

---

## 1. Choix de Build et Personnalisation des Images

### A. Le Reverse Proxy (dossier proxy)
* **Image de base :** `nginx:alpine` pour sa legerete et sa rapidite.
* **Operations OS :** Mise a jour des paquets `apk` et installation de l'outil `curl` pour les tests de sante, suivis d'un nettoyage du cache pour reduire la taille finale de l'image.
* **Configuration :** Suppression du fichier de configuration par defaut de Nginx et integration d'un fichier `nginx.conf` personnalise pour router le trafic racine (`/`) vers le front et le trafic `/api` vers le back.
* **Ports ouverts :** Port `80` en interne.

### B. Le Front-End (dossier front)
* **Image de base :** `nginx:alpine`.
* **Operations OS :** Installation de `curl` et nettoyage du cache des paquets.
* **Configuration :** Integration d'une page `index.html` personnalisee et application de permissions strictes sur les fichiers (utilisation de `chown` et `chmod`) pour des raisons de securite.
* **Ports ouverts :** Port `80` en interne.

### C. Le Back-End (dossier back)
* **Image de base :** `python:3.11-slim`.
* **Arguments de build :** Utilisation d'un `ARG` pour definir dynamiquement l'environnement (production).
* **Operations OS :** Mise a jour via `apt-get`, installation de `curl`, et nettoyage des listes de paquets.
* **Securite :** Creation d'un utilisateur dedie non-root (`appuser`) pour executer l'application, afin d'eviter l'elevation de privileges en cas de faille.
* **Dependances et code :** Copie du fichier `requirements.txt`, installation des paquets, et integration du script Python (`app.py`).
* **Ports ouverts :** Port `5000` en interne.

---

## 2. Arguments au Run et Orchestration (docker-compose.yml)

Au moment du lancement via Docker Compose, chaque conteneur recoit des parametres de configuration et des limites de ressources :

* **Variables d'environnement :** Transmission de parametres de configuration au runtime (ex: modes de production).
* **Quotas de ressources :**
  * Proxy : Limite a `0.30` vCPU et `128` Mo de RAM.
  * Front : Limite a `0.50` vCPU et `256` Mo de RAM.
  * Back : Limite a `1.0` vCPU et `512` Mo de RAM.
* **Healthchecks :** Integration d'une verification automatique de l'etat de sante des services via `curl` a intervalle regulier.

- **Persistance des données (Volumes Docker) :**
  * Utilisation de deux volumes nommes (`mtg_data` et `mtg_images`) attaches au conteneur `back`.
  * `mtg_data` garantit la conservation de la base de données (collection, decks) même en cas de suppression du conteneur.
  * `mtg_images` permet de stocker en cache les visuels des cartes téléchargés depuis l'API externe pour optimiser les performances.

---

## 3. Guide de Demarrage

Pour lancer l'infrastructure :

1. Ouvrir le terminal a la racine du projet.
2. Executer la commande suivante :
   ```bash
   docker compose up --build
   ```
3. Acceder aux services :
   * Interface Web : `http://localhost:8080/`