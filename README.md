# 📘 GMAO – Gestion Maintenance Assistée par Ordinateur  
**Application Web interne – Python / Flask / Postgres / Docker**

---

## 📌 Présentation

GMAO est une application web permettant de gérer :

- ✔️ les **clients**
- ✔️ leurs **sites / agences**
- ✔️ leurs **matériels**
- ✔️ les **tickets** (incidents / demandes)
- ✔️ les **commentaires** des techniciens
- ✔️ la **gestion multi-matériel** par ticket
- ✔️ la **gestion multi-site** par ticket
- ✔️ l’authentification des utilisateurs
- ✔️ les changements de statut & historique interne

C’est une solution légère, auto-hébergeable et pensée pour un usage interne en entreprise.

---

## 🏗️ Architecture technique

gmao/
│── app/
│ ├── main.py # Application Flask
│ ├── templates/ # Pages HTML (Jinja2)
│ ├── static/ # CSS, JS, images
│ ├── requirements.txt # Dépendances Python
│
│── docker-compose.yml # Stack Docker
│── .gitignore
│── README.md


---

## 🚀 Technologies utilisées

- **Backend :** Python 3 + Flask + SQLAlchemy  
- **Base de données :** PostgreSQL 17  
- **Frontend :** HTML / CSS / JS (Jinja2)  
- **Sessions sécurisées :** Flask  
- **ORM :** SQLAlchemy  
- **Déploiement :** Docker + Portainer

---

## 🧰 Fonctionnalités

### ✔️ Clients  
- Ajout / modification  
- Code automatique `CLT-0001`  
- Rattachés à des sites et du matériel  

### ✔️ Sites / Agences  
- Dépendants d’un client  
- Adresse, ville, notes  
- Sélection multi-site dans les tickets  

### ✔️ Matériel  
- Matériel rattaché à un client  
- Type, modèle, numéro de série  
- Dates d’installation et fin de garantie  
- Statut (En service / HS / Retiré)  
- Fiche matériel + édition complète  

### ✔️ Tickets  
- Ticket rattaché à un client  
- Multi-matériel  
- Multi-site  
- Commentaires internes  
- Priorité, type, état  
- Ouverture / clôture automatiques  

### ✔️ Authentification  
- Utilisateurs internes  
- Rôles : technicien / admin  
- Accès bloqué si non connecté  
- Redirection automatique vers login  

---

## 🐳 Installation avec Docker

### 1. Cloner le dépôt

```bash
git clone https://github.com/<ton_user>/gmao.git
cd gmao
```

## 2. Lancer la stack
```bash
docker compose up -d
```

L’application Flask et PostgreSQL démarrent automatiquement.

## 🔑 Variables d’environnement
```bash
DATABASE_URL=postgresql+psycopg2://gmao:change_me@gmao_db:5432/gmao
SECRET_KEY=une_chaine_secrete
GMAO_ADMIN_LOGIN=admin
GMAO_ADMIN_PASSWORD=motdepasse
GMAO_ADMIN_NAME=Administrateur
```

Au premier lancement, l’utilisateur admin est créé automatiquement.