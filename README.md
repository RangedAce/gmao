# 📘 GMAO – Gestion Maintenance Assistée par Ordinateur  
**Application web légère – Flask + PostgreSQL + Docker**

---

## 📌 Présentation

GMAO est une application web interne permettant de gérer :  

- ✔️ les **clients**  
- ✔️ leurs **sites / agences**  
- ✔️ leurs **matériels**  
- ✔️ les **tickets** de support  
- ✔️ les **commentaires** des techniciens  
- ✔️ les statuts, priorités, historiques  
- ✔️ la gestion **multi-sites** et **multi-matériels** par ticket  
- ✔️ l’authentification interne (admin / technicien)

L’objectif est d’avoir un outil simple, auto-hébergeable, adapté pour un service informatique ou une petite entreprise.

---

# 🏗️ Architecture du projet

Ton dépôt contient uniquement le **code de l’application** :

```
gmao/
├── main.py               # App Flask
├── requirements.txt      # Dépendances Python
├── templates/            # Pages HTML (Jinja2)
├── static/               # CSS / JS / images
└── README.md
```

L’environnement Docker (db, app, webhook, etc.) peut être géré depuis l’extérieur  
(ex : `/opt/docker/gmao` sur le serveur).

Cela permet d'utiliser ce dépôt exclusivement pour le code de l'application.

---

# 🚀 Technologies principales

- **Backend :** Python 3.12 + Flask  
- **ORM :** SQLAlchemy  
- **Base de données :** PostgreSQL 17  
- **Frontend :** HTML/CSS (Jinja2)  
- **Déploiement :** Docker / Docker Compose  
- **Migrations & initialisation :** Python automatisé au démarrage  
- **Auth :** Sessions Flask + rôles utilisateurs  

---

# 🧩 Fonctionnalités

### ✔️ Clients  
- Création / édition  
- Codes auto-générés (`CLT-0001`, etc.)  
- Matériels & sites liés  

### ✔️ Sites  
- Reliés à un client  
- Multi-sélection dans un ticket  

### ✔️ Matériels  
- Type, marque, modèle  
- Numéro de série  
- Date d'installation & garantie  
- Statut (OK / HS / Retiré)  
- Assignation à client + site  

### ✔️ Tickets  
- Multi-sites  
- Multi-matériels  
- Commentaires internes  
- Historique  
- Priorité / type / statut  
- Clôture automatique si résolu  

### ✔️ Authentification & rôles  
- Admin  
- Technicien  
- Redirection automatique si non connecté  

---

# 🐳 Exemple de stack Docker (prête à l’emploi)

Voici une stack Docker **externe au repo**, à placer par exemple dans :  
`/opt/docker/gmao/docker-compose.yml`

> 👉 **Ce docker-compose n’est pas dans le dépôt Git**, pour éviter d’exposer les mots de passe / secrets.

```yaml
version: "3.9"

services:
  db:
    image: postgres:17-alpine
    container_name: gmao_db
    restart: unless-stopped
    environment:
      - POSTGRES_DB=gmao
      - POSTGRES_USER=gmao
      - POSTGRES_PASSWORD=change_me
    volumes:
      - /opt/docker/gmao/db:/var/lib/postgresql/data

  app:
    image: python:3.12-slim
    container_name: gmao_app
    restart: unless-stopped
    working_dir: /app
    environment:
      - TZ=Europe/Paris
      - DATABASE_URL=postgresql+psycopg2://gmao:change_me@gmao_db:5432/gmao
      - SECRET_KEY=change_me_super_secret
      - GMAO_ADMIN_NAME=Admin
      - GMAO_ADMIN_ROLE=admin
      - GMAO_ADMIN_LOGIN=admin
      - GMAO_ADMIN_PASSWORD=admin
    depends_on:
      - db
    ports:
      - "7894:8000"
    volumes:
      - /opt/docker/gmao/app:/app
    command: >
      sh -c "pip install --no-cache-dir -r requirements.txt &&
             python main.py"
```

---

# 🔧 Installation locale (sans Docker)

```bash
pip install -r requirements.txt
python main.py
```

L’application tourne sur :  
**http://localhost:8000**

---

# 🔑 Variables d’environnement

| Variable | Description |
|---------|-------------|
| `DATABASE_URL` | URL SQLAlchemy vers PostgreSQL |
| `SECRET_KEY` | Clé secrète Flask |
| `GMAO_ADMIN_LOGIN` | Login admin créé au 1er lancement |
| `GMAO_ADMIN_PASSWORD` | Mot de passe admin |
| `GMAO_ADMIN_NAME` | Nom affiché |
| `GMAO_ADMIN_ROLE` | admin / technicien |

---

# 🔄 Webhook GitHub (déploiement auto – optionnel)

Tu peux ajouter un conteneur externe qui :

- reçoit un webhook GitHub,
- exécute `git pull`,
- recharge instantanément l’app.

Exemple minimal :

```yaml
gmao-webhook:
  image: python:3.12-slim
  container_name: gmao_webhook
  restart: unless-stopped
  working_dir: /webhook
  volumes:
    - /opt/docker/gmao-webhook:/webhook
    - /opt/docker/gmao/app:/repo_app
  environment:
    - GMAO_WEBHOOK_SECRET=secret_webhook
    - REPO_PATH=/repo_app
    - BRANCH=master
  command: >
    sh -c "apt-get update &&
           apt-get install -y git &&
           pip install flask &&
           python webhook.py"
  ports:
    - "9000:9000"
```

---

# 📄 Licence

Projet librement utilisable et modifiable.

---

# 📬 Contact

Pour toute question ou suggestion :  
→ ouvre une issue sur GitHub.
