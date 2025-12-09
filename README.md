📘 GMAO – Gestion Maintenance Assistée par Ordinateur

Application Web interne – Python / Flask / Postgres / Docker

📌 Présentation

GMAO est une application web légère permettant de gérer :

✔️ les clients

✔️ leurs sites / agences

✔️ leurs matériels

✔️ les tickets (incidents / demandes)

✔️ les commentaires des techniciens

✔️ la gestion multi-matériel et multi-site pour chaque ticket

✔️ l’authentification des utilisateurs

✔️ les rôles internes

✔️ un historique propre de chaque intervention

L’application est pensée pour un usage interne (techniciens / support), mais peut évoluer vers un client-portal.

🏗️ Architecture technique
gmao/
│── app/
│   ├── main.py                # Application Flask
│   ├── templates/             # Pages HTML (Jinja2)
│   ├── static/                # CSS, JS, images
│   ├── requirements.txt       # Dépendances Python
│
│── docker-compose.yml         # Stack docker
│── .gitignore
│── README.md

🚀 Technologies

Backend : Python 3 + Flask + SQLAlchemy

Base de données : PostgreSQL 17

Frontend : HTML / CSS / JS (Jinja2)

Auth : sessions sécurisées Flask

ORM : SQLAlchemy (relations N-N pour tickets ↔ matériels et tickets ↔ sites)

Déploiement : Docker + Portainer

🧰 Fonctionnalités principales
✔️ Gestion des Clients

Ajout / modification

Code automatique CLT-0001

Sites associés (agences)

✔️ Gestion des Sites / Agences

Rattachés à un client

Adresse, ville, notes

Utilisés pour préciser où se passe l'incident

✔️ Gestion du Matériel

Par client

Type, modèle, numéro de série

Dates (installation, fin de garantie)

Statut (en service / HS / retiré)

Éditable

✔️ Tickets

Création d’un ticket pour un client

Multiple matériels concernés

Multiple sites concernés

Priorité, type, état

Historique des commentaires

Changement de statut (ouvert / en cours / résolu / clos)

✔️ Authentification interne

Login + session

Utilisateurs (techniciens, admin, etc.)

Restriction automatique : accès interdit sans être connecté

🐳 Installation via Docker
1. Cloner le repo
git clone https://github.com/<votre_user>/gmao.git
cd gmao

2. Lancer la stack
docker compose up -d


La BDD et l’application Flask se lancent automatiquement.

🔑 Variables d’environnement

À mettre dans votre stack Portainer ou dans un fichier .env :

DATABASE_URL=postgresql+psycopg2://gmao:change_me@gmao_db:5432/gmao
SECRET_KEY=une_chaine_secrete
GMAO_ADMIN_LOGIN=admin
GMAO_ADMIN_PASSWORD=motdepasse
GMAO_ADMIN_NAME=Administrateur


L’utilisateur admin est créé automatiquement au premier lancement.

🔄 Mise à jour via Git
Sur le serveur :
cd /opt/docker/gmao/app
git pull
docker restart gmao_app

(optionnel) Script automatique

Créer /usr/local/bin/gmao-update :

#!/bin/bash
cd /opt/docker/gmao/app
git pull
docker restart gmao_app


Puis :

sudo chmod +x /usr/local/bin/gmao-update


Utilisation :

sudo gmao-update

🧪 Structure de la base de données
Clients

→ Sites
→ Matériels
→ Tickets
→ Ticket ↔ Sites (relation N-N)
→ Ticket ↔ Matériels (relation N-N)
→ Commentaires
→ Utilisateurs

📄 Licence

Par défaut : propriétaire (usage interne uniquement).
Tu peux switch en MIT, GPL ou autre si tu veux.

🤝 Contributions

Fork du projet

PR bienvenues

Issues pour les bugs / idées