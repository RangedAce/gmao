import os
from datetime import datetime, timedelta

from flask import (
    Flask, render_template, request,
    redirect, url_for, session, jsonify
)
import difflib
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import or_, inspect

# ==========================
#  CONFIG
# ==========================
app = Flask(__name__)

app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg2://gmao:change_me@gmao_db:5432/gmao"
)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-secret-change-me")

db = SQLAlchemy(app)

# ==========================
#  MODELES
# ==========================

class Client(db.Model):
    __tablename__ = "clients"
    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(128), nullable=False)
    contract_type = db.Column(db.String(32), nullable=False, default="none")  # none | credit_time | credit_point
    contract_balance = db.Column(db.Float, nullable=True)  # heures ou points selon le type


class ContractLog(db.Model):
    __tablename__ = "contract_logs"
    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey("clients.id"), nullable=False)
    ticket_id = db.Column(db.Integer, db.ForeignKey("tickets.id"), nullable=False)
    kind = db.Column(db.String(32), nullable=False)  # credit_time | credit_point
    amount = db.Column(db.Float, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now)
    note = db.Column(db.Text, nullable=True)

    client = db.relationship("Client", backref="contract_logs")


class MaintenanceContract(db.Model):
    __tablename__ = "maintenance_contracts"
    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey("clients.id"), nullable=False)
    numero = db.Column(db.String(128), nullable=False)
    duree = db.Column(db.String(64), nullable=True)
    type_contrat = db.Column(db.String(128), nullable=True)
    date_effet = db.Column(db.Date, nullable=True)
    date_renouvellement = db.Column(db.Date, nullable=True)
    conditions = db.Column(db.Text, nullable=True)
    prix_total = db.Column(db.Float, nullable=True)
    resilie = db.Column(db.Boolean, nullable=False, default=False)
    reconductible = db.Column(db.Boolean, nullable=False, default=False)

    client = db.relationship("Client", backref="maintenance_contracts")


class Site(db.Model):
    __tablename__ = "sites"
    id = db.Column(db.Integer, primary_key=True)

    id_client = db.Column(db.Integer, db.ForeignKey("clients.id"), nullable=False)
    nom = db.Column(db.String(128), nullable=False)
    adresse = db.Column(db.String(255), nullable=True)
    ville = db.Column(db.String(128), nullable=True)
    notes = db.Column(db.Text, nullable=True)

    client = db.relationship("Client", backref="sites")


class MaterielCategory(db.Model):
    __tablename__ = "materiel_categories"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), nullable=False, unique=True)

    types = db.relationship("MaterielType", backref="category", cascade="all,delete-orphan")


class MaterielType(db.Model):
    __tablename__ = "materiel_types"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey("materiel_categories.id"), nullable=False)

    __table_args__ = (
        db.UniqueConstraint("name", "category_id", name="uq_type_per_category"),
    )


class Materiel(db.Model):
    __tablename__ = "materiels"
    id = db.Column(db.Integer, primary_key=True)

    id_client = db.Column(db.Integer, db.ForeignKey("clients.id"), nullable=False)
    type = db.Column(db.String(64), nullable=False)
    type_id = db.Column(db.Integer, db.ForeignKey("materiel_types.id"), nullable=True)
    category_id = db.Column(db.Integer, db.ForeignKey("materiel_categories.id"), nullable=True)
    modele = db.Column(db.String(128), nullable=False)
    numero_serie = db.Column(db.String(128), nullable=False)
    date_installation = db.Column(db.String(20), nullable=True)
    garantie_fin = db.Column(db.String(20), nullable=True)
    statut = db.Column(db.String(32), nullable=False, default="en service")

    client = db.relationship("Client", backref="materiels")
    materiel_type = db.relationship("MaterielType", backref="materiels")
    category = db.relationship("MaterielCategory", backref="materiels")


class User(db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(128), nullable=False)
    login = db.Column(db.String(64), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(32), nullable=False, default="technicien")


class TicketMateriel(db.Model):
    """
    Table de liaison N–N entre Ticket et Materiel.
    Un ticket peut avoir plusieurs matériels,
    et un matériel peut apparaître dans plusieurs tickets.
    """
    __tablename__ = "ticket_materiels"

    ticket_id = db.Column(db.Integer, db.ForeignKey("tickets.id"), primary_key=True)
    materiel_id = db.Column(db.Integer, db.ForeignKey("materiels.id"), primary_key=True)

class TicketSite(db.Model):
    __tablename__ = "ticket_sites"

    ticket_id = db.Column(db.Integer, db.ForeignKey("tickets.id"), primary_key=True)
    site_id = db.Column(db.Integer, db.ForeignKey("sites.id"), primary_key=True)


class Ticket(db.Model):
    __tablename__ = "tickets"
    id = db.Column(db.Integer, primary_key=True)

    id_client = db.Column(db.Integer, db.ForeignKey("clients.id"), nullable=False)
    assigned_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    category_id = db.Column(db.Integer, db.ForeignKey("materiel_categories.id"), nullable=True)
    materiel_type_id = db.Column(db.Integer, db.ForeignKey("materiel_types.id"), nullable=True)

    titre = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    type = db.Column(db.String(32), nullable=False)
    priorite = db.Column(db.String(16), nullable=False)
    etat = db.Column(db.String(32), nullable=False, default="ouvert")

    date_ouverture = db.Column(db.DateTime, default=datetime.now)
    date_cloture = db.Column(db.DateTime, nullable=True)

    client = db.relationship("Client")
    category = db.relationship("MaterielCategory")
    materiel_type = db.relationship("MaterielType")
    assigned_user = db.relationship("User", foreign_keys=[assigned_user_id])

    materiels = db.relationship(
        "Materiel",
        secondary="ticket_materiels",
        lazy="joined",
    )

    sites = db.relationship(
        "Site",
        secondary="ticket_sites",
        lazy="joined",
    )


class TicketComment(db.Model):
    __tablename__ = "ticket_comments"
    id = db.Column(db.Integer, primary_key=True)

    ticket_id = db.Column(db.Integer, db.ForeignKey("tickets.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, nullable=True)
    previous_content = db.Column(db.Text, nullable=True)
    last_editor_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)

    ticket = db.relationship("Ticket", backref="comments")
    user = db.relationship("User", foreign_keys=[user_id], backref="comments")
    last_editor = db.relationship("User", foreign_keys=[last_editor_id], backref="edited_comments")

    @property
    def is_edited(self):
        return self.updated_at is not None


def _get_current_user():
    if "user_id" not in session:
        return None
    return User.query.get(session["user_id"])


def _require_admin():
    user = _get_current_user()
    return user if user and user.role == "admin" else None


# ==========================
#  INIT BDD + USER ADMIN
# ==========================
def ensure_schema():
    """Crée les tables/colonnes manquantes au démarrage (fallback sans migrations Alembic)."""
    engine = db.engine
    with engine.begin() as conn:
        inspector = inspect(conn)
        conn.execute(db.text("""
        CREATE TABLE IF NOT EXISTS materiel_categories (
            id SERIAL PRIMARY KEY,
            name VARCHAR(128) UNIQUE NOT NULL
        );
        """))
        conn.execute(db.text("""
        CREATE TABLE IF NOT EXISTS materiel_types (
            id SERIAL PRIMARY KEY,
            name VARCHAR(128) NOT NULL,
            category_id INTEGER NOT NULL REFERENCES materiel_categories(id),
            CONSTRAINT uq_type_per_category UNIQUE (name, category_id)
        );
        """))
        conn.execute(db.text("""
        ALTER TABLE materiels
        ADD COLUMN IF NOT EXISTS category_id INTEGER REFERENCES materiel_categories(id);
        """))
        conn.execute(db.text("""
        ALTER TABLE materiels
        ADD COLUMN IF NOT EXISTS type_id INTEGER REFERENCES materiel_types(id);
        """))
        conn.execute(db.text("""
        ALTER TABLE tickets
        ADD COLUMN IF NOT EXISTS category_id INTEGER REFERENCES materiel_categories(id);
        """))
        conn.execute(db.text("""
        ALTER TABLE tickets
        ADD COLUMN IF NOT EXISTS materiel_type_id INTEGER REFERENCES materiel_types(id);
        """))
        conn.execute(db.text("""
        ALTER TABLE tickets
        ADD COLUMN IF NOT EXISTS assigned_user_id INTEGER REFERENCES users(id);
        """))
        conn.execute(db.text("CREATE INDEX IF NOT EXISTS ix_materiels_category ON materiels(category_id);"))
        conn.execute(db.text("CREATE INDEX IF NOT EXISTS ix_materiels_type ON materiels(type_id);"))
        conn.execute(db.text("CREATE INDEX IF NOT EXISTS ix_tickets_category ON tickets(category_id);"))
        conn.execute(db.text("CREATE INDEX IF NOT EXISTS ix_tickets_materiel_type ON tickets(materiel_type_id);"))
        conn.execute(db.text("""
        ALTER TABLE clients
        ADD COLUMN IF NOT EXISTS contract_type VARCHAR(32) NOT NULL DEFAULT 'none';
        """))
        conn.execute(db.text("""
        ALTER TABLE clients
        ADD COLUMN IF NOT EXISTS contract_balance FLOAT;
        """))
        conn.execute(db.text("""
        CREATE TABLE IF NOT EXISTS contract_logs (
            id SERIAL PRIMARY KEY,
            client_id INTEGER NOT NULL REFERENCES clients(id),
            ticket_id INTEGER NOT NULL REFERENCES tickets(id),
            kind VARCHAR(32) NOT NULL,
            amount FLOAT NOT NULL,
            created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now(),
            note TEXT
        );
        """))
        conn.execute(db.text("CREATE INDEX IF NOT EXISTS ix_contract_logs_client ON contract_logs(client_id);"))
        conn.execute(db.text("CREATE INDEX IF NOT EXISTS ix_contract_logs_ticket ON contract_logs(ticket_id);"))
        conn.execute(db.text("""
        CREATE TABLE IF NOT EXISTS maintenance_contracts (
            id SERIAL PRIMARY KEY,
            client_id INTEGER NOT NULL REFERENCES clients(id),
            numero VARCHAR(128) NOT NULL,
            duree VARCHAR(64),
            type_contrat VARCHAR(128),
            date_effet DATE,
            date_renouvellement DATE,
            conditions TEXT,
            prix_total FLOAT,
            resilie BOOLEAN NOT NULL DEFAULT FALSE,
            reconductible BOOLEAN NOT NULL DEFAULT FALSE
        );
        """))
        conn.execute(db.text("CREATE INDEX IF NOT EXISTS ix_maintenance_contracts_client ON maintenance_contracts(client_id);"))

        # Fallback évolutif pour les colonnes ajoutées après coup
        columns_to_add = {
            "materiels": [
                ("category_id", "INTEGER REFERENCES materiel_categories(id)"),
                ("type_id", "INTEGER REFERENCES materiel_types(id)"),
            ],
            "tickets": [
                ("category_id", "INTEGER REFERENCES materiel_categories(id)"),
                ("materiel_type_id", "INTEGER REFERENCES materiel_types(id)"),
                ("assigned_user_id", "INTEGER REFERENCES users(id)"),
            ],
            "clients": [
                ("contract_type", "VARCHAR(32) NOT NULL DEFAULT 'none'"),
                ("contract_balance", "FLOAT"),
            ],
        }

        for table_name, cols in columns_to_add.items():
            existing = {col["name"] for col in inspector.get_columns(table_name)}
            for col_name, ddl in cols:
                if col_name not in existing:
                    conn.execute(db.text(f"ALTER TABLE {table_name} ADD COLUMN {col_name} {ddl};"))


with app.app_context():
    db.create_all()
    ensure_schema()

    admin_login = os.getenv("GMAO_ADMIN_LOGIN")
    admin_name = os.getenv("GMAO_ADMIN_NAME", "Admin")
    admin_password = os.getenv("GMAO_ADMIN_PASSWORD")
    admin_role = os.getenv("GMAO_ADMIN_ROLE", "admin")

    if admin_login and admin_password:
        if not User.query.filter_by(login=admin_login).first():
            u = User(
                full_name=admin_name,
                login=admin_login,
                role=admin_role,
                password_hash=generate_password_hash(admin_password),
            )
            db.session.add(u)
            db.session.commit()
            print(f"[GMAO] Utilisateur {admin_role} créé : {admin_login}")


# ==========================
#  HELPERS
# ==========================
@app.context_processor
def inject_user():
    current_user = None
    if "user_id" in session:
        current_user = User.query.get(session["user_id"])
    is_admin = bool(current_user and current_user.role == "admin")
    return dict(current_user=current_user, is_admin=is_admin)


# 🔒 Avant chaque requête : tout est bloqué sauf login/logout/static
@app.before_request
def require_login():
    # endpoints autorisés sans login
    public_endpoints = {"login", "static"}
    if request.endpoint in public_endpoints:
        return

    # autoriser logout même si pas loggé (ça clear juste la session)
    if request.endpoint == "logout":
        return

    if "user_id" not in session:
        next_url = request.path
        return redirect(url_for("login", next=next_url))


# ==========================
#  AUTH
# ==========================
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        login_value = request.form.get("login")
        password = request.form.get("password")

        user = User.query.filter_by(login=login_value).first()
        if not user or not check_password_hash(user.password_hash, password):
            return render_template("login.html", error="Identifiants invalides")

        session["user_id"] = user.id
        next_url = request.args.get("next")
        return redirect(next_url or url_for("index"))

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


# ==========================
#  CLIENTS
# ==========================
@app.route("/")
def index():
    now = datetime.now()
    threshold = now - timedelta(hours=24)
    tickets_open = Ticket.query.filter(Ticket.etat != "cloture").all()
    tickets_unhandled = 0
    state_counts = {}
    assigned_counts = {}

    for t in tickets_open:
        state_counts[t.etat] = state_counts.get(t.etat, 0) + 1

        assigned_label = t.assigned_user.full_name if t.assigned_user else "Non assigne"
        assigned_counts[assigned_label] = assigned_counts.get(assigned_label, 0) + 1

        last_activity = t.date_ouverture
        for c in t.comments:
            activity_time = c.updated_at or c.created_at
            if activity_time and activity_time > last_activity:
                last_activity = activity_time
        if last_activity < threshold:
            tickets_unhandled += 1

    return render_template(
        "index.html",
        tickets_unhandled=tickets_unhandled,
        state_counts=state_counts,
        assigned_counts=assigned_counts,
    )


@app.route("/clients")
def liste_clients():
    code_query = (request.args.get("code") or "").strip()
    name_query = (request.args.get("nom") or "").strip()

    client_query = Client.query
    if code_query:
        code_digits = code_query.replace("CLT-", "").strip()
        try:
            code_int = int(code_digits)
            client_query = client_query.filter(Client.id == code_int)
        except ValueError:
            client_query = client_query.filter(Client.id == -1)
    if name_query:
        client_query = client_query.filter(Client.nom.ilike(f"%{name_query}%"))

    clients = client_query.order_by(Client.id).all()
    return render_template("clients.html", clients=clients, filters={"code": code_query, "nom": name_query})


@app.route("/clients/nouveau", methods=["GET", "POST"])
def nouveau_client():
    if request.method == "POST":
        nom = request.form.get("nom", "").strip()
        contract_type = request.form.get("contract_type", "none")
        contract_balance = request.form.get("contract_balance")
        balance_value = float(contract_balance) if contract_balance else None
        if not nom:
            return render_template("nouveau_client.html", error="Nom obligatoire")
        db.session.add(Client(nom=nom, contract_type=contract_type, contract_balance=balance_value))
        db.session.commit()
        return redirect(url_for("liste_clients"))
    return render_template("nouveau_client.html")
@app.route("/clients/<int:id>/edit", methods=["GET", "POST"])
def edit_client(id):
    client = Client.query.get_or_404(id)

    if request.method == "POST":
        nom = request.form.get("nom", "").strip()
        contract_type = request.form.get("contract_type", "none")
        contract_balance = request.form.get("contract_balance")
        balance_value = float(contract_balance) if contract_balance else None
        if not nom:
            return render_template("edit_client.html", client=client, error="Le nom est obligatoire")
        client.nom = nom
        client.contract_type = contract_type
        client.contract_balance = balance_value
        db.session.commit()
        return redirect(url_for("liste_clients"))

    return render_template("edit_client.html", client=client)

@app.route("/clients/<int:id>")
def client_fiche(id):
    client = Client.query.get_or_404(id)
    tickets = Ticket.query.filter_by(id_client=id).order_by(Ticket.id.desc()).all()
    materiels = Materiel.query.filter_by(id_client=id).order_by(Materiel.id).all()
    logs = ContractLog.query.filter_by(client_id=id).order_by(ContractLog.created_at.desc()).all()
    maintenance_contracts = MaintenanceContract.query.filter_by(client_id=id).order_by(
        MaintenanceContract.date_effet.desc(), MaintenanceContract.id.desc()
    ).all()
    return render_template(
        "client_fiche.html",
        client=client,
        tickets=tickets,
        materiels=materiels,
        contract_logs=logs,
        maintenance_contracts=maintenance_contracts,
    )

@app.route("/clients/<int:client_id>/sites/nouveau", methods=["GET", "POST"])
def nouveau_site(client_id):
    client = Client.query.get_or_404(client_id)

    if request.method == "POST":
        nom = request.form.get("nom", "").strip()
        adresse = request.form.get("adresse", "").strip()
        ville = request.form.get("ville", "").strip()
        notes = request.form.get("notes", "").strip()

        if not nom:
            return render_template("site_nouveau.html", client=client, error="Le nom du site est obligatoire")

        s = Site(
            id_client=client.id,
            nom=nom,
            adresse=adresse,
            ville=ville,
            notes=notes,
        )
        db.session.add(s)
        db.session.commit()
        return redirect(url_for("client_fiche", id=client.id))

    return render_template("site_nouveau.html", client=client)
@app.route("/api/client/<int:client_id>/data")
def api_client_data(client_id):
    # Vérifie que le client existe
    client = Client.query.get_or_404(client_id)

    materiels = Materiel.query.filter_by(id_client=client.id).order_by(Materiel.id).all()
    sites = Site.query.filter_by(id_client=client.id).order_by(Site.nom).all()

    return jsonify({
        "materiels": [
            {
                "id": m.id,
                "label": f"{m.type} {m.modele} ({m.numero_serie})",
                "category_id": m.category_id,
                "type_id": m.type_id,
            }
            for m in materiels
        ],
        "sites": [
            {
                "id": s.id,
                "label": f"{s.nom}" + (f" ({s.ville})" if s.ville else "")
            }
            for s in sites
        ]
    })

# ==========================
#  MATERIELS
# ==========================
@app.route("/materiels")
def liste_materiels():
    return render_template(
        "materiels.html",
        materiels=Materiel.query.order_by(Materiel.id).all(),
    )


@app.route("/materiels/categories", methods=["GET", "POST"])
def gestion_categories():
    admin = _require_admin()
    if not admin:
        return redirect(url_for("index"))

    error = None
    success = False

    if request.method == "POST":
        action = request.form.get("action")
        if action == "add_category":
            name = request.form.get("name", "").strip()
            if not name:
                error = "Nom de catégorie obligatoire."
            elif MaterielCategory.query.filter_by(name=name).first():
                error = "Cette catégorie existe déjà."
            else:
                db.session.add(MaterielCategory(name=name))
                db.session.commit()
                success = True
        if action == "add_type":
            name = request.form.get("type_name", "").strip()
            category_id = request.form.get("category_id")
            category = MaterielCategory.query.get(category_id)
            if not category or not name:
                error = "Nom de type et catégorie requis."
            elif MaterielType.query.filter_by(name=name, category_id=category.id).first():
                error = "Ce type existe déjà dans cette catégorie."
            else:
                db.session.add(MaterielType(name=name, category_id=category.id))
                db.session.commit()
                success = True

    categories = MaterielCategory.query.order_by(MaterielCategory.name).all()
    types = MaterielType.query.order_by(MaterielType.name).all()
    return render_template(
        "materiel_categories.html",
        categories=categories,
        types=types,
        error=error,
        success=success,
    )


@app.route("/materiels/nouveau", methods=["GET", "POST"])
def nouveau_materiel():
    clients = Client.query.order_by(Client.nom).all()
    categories = MaterielCategory.query.order_by(MaterielCategory.name).all()
    types = MaterielType.query.order_by(MaterielType.name).all()

    if request.method == "POST":
        type_id = request.form.get("type_id")
        category_id = request.form.get("category_id")
        materiel_type = MaterielType.query.get(type_id) if type_id else None

        m = Materiel(
            id_client=request.form.get("id_client"),
            type=materiel_type.name if materiel_type else request.form.get("type"),
            type_id=materiel_type.id if materiel_type else None,
            category_id=materiel_type.category_id if materiel_type else category_id,
            modele=request.form.get("modele"),
            numero_serie=request.form.get("numero_serie"),
            date_installation=request.form.get("date_installation"),
            garantie_fin=request.form.get("garantie_fin"),
            statut=request.form.get("statut"),
        )
        db.session.add(m)
        db.session.commit()
        return redirect(url_for("liste_materiels"))

    return render_template("nouveau_materiel.html", clients=clients, categories=categories, types=types)


@app.route("/materiels/<int:id>")
def materiel_fiche(id):
    return render_template("materiel_fiche.html", m=Materiel.query.get_or_404(id))
@app.route("/materiels/<int:id>/edit", methods=["GET", "POST"])
def materiel_edit(id):
    materiel = Materiel.query.get_or_404(id)
    clients = Client.query.order_by(Client.nom).all()
    categories = MaterielCategory.query.order_by(MaterielCategory.name).all()
    types = MaterielType.query.order_by(MaterielType.name).all()

    if request.method == "POST":
        materiel.id_client = request.form.get("id_client")
        type_id = request.form.get("type_id")
        category_id = request.form.get("category_id")
        materiel_type = MaterielType.query.get(type_id) if type_id else None

        materiel.type = materiel_type.name if materiel_type else materiel.type
        materiel.type_id = materiel_type.id if materiel_type else None
        materiel.category_id = materiel_type.category_id if materiel_type else category_id
        materiel.modele = request.form.get("modele")
        materiel.numero_serie = request.form.get("numero_serie")
        materiel.date_installation = request.form.get("date_installation")
        materiel.garantie_fin = request.form.get("garantie_fin")
        materiel.statut = request.form.get("statut")

        db.session.commit()
        return redirect(url_for("materiel_fiche", id=materiel.id))

    return render_template("materiel_edit.html", m=materiel, clients=clients, categories=categories, types=types)


# ==========================
#  TICKETS
# ==========================
@app.route("/tickets")
def liste_tickets():
    client_id = request.args.get("client_id", type=int)
    materiel_type_id = request.args.get("materiel_type_id", type=int)
    filters = {
        "client_id": client_id,
        "client_nom": (request.args.get("client_nom") or "").strip(),
        "materiel_type_id": materiel_type_id,
        "materiel_search": (request.args.get("materiel_search") or "").strip(),
        "titre": (request.args.get("titre") or "").strip(),
        "type": request.args.get("type") or "",
        "priorite": request.args.get("priorite") or "",
        "etat": request.args.get("etat") or "",
        "date_debut": request.args.get("date_debut") or "",
        "date_fin": request.args.get("date_fin") or "",
    }

    query = Ticket.query.join(Client).outerjoin(MaterielType, Ticket.materiel_type)

    if filters["client_id"]:
        query = query.filter(Ticket.id_client == filters["client_id"])
    if filters["client_nom"]:
        query = query.filter(Client.nom.ilike(f"%{filters['client_nom']}%"))

    if filters["materiel_type_id"]:
        query = query.filter(
            or_(
                Ticket.materiel_type_id == filters["materiel_type_id"],
                Ticket.materiels.any(Materiel.type_id == filters["materiel_type_id"]),
            )
        )
    if filters["materiel_search"]:
        search_value = f"%{filters['materiel_search']}%"
        query = query.filter(
            Ticket.materiels.any(
                or_(
                    Materiel.type.ilike(search_value),
                    Materiel.modele.ilike(search_value),
                    Materiel.numero_serie.ilike(search_value),
                )
            )
        )

    if filters["titre"]:
        query = query.filter(Ticket.titre.ilike(f"%{filters['titre']}%"))
    if filters["type"]:
        query = query.filter(Ticket.type == filters["type"])
    if filters["priorite"]:
        query = query.filter(Ticket.priorite == filters["priorite"])
    if filters["etat"]:
        query = query.filter(Ticket.etat == filters["etat"])

    if filters["date_debut"]:
        try:
            date_start = datetime.strptime(filters["date_debut"], "%Y-%m-%d")
            query = query.filter(Ticket.date_ouverture >= date_start)
        except ValueError:
            pass
    if filters["date_fin"]:
        try:
            date_end = datetime.strptime(filters["date_fin"], "%Y-%m-%d") + timedelta(days=1)
            query = query.filter(Ticket.date_ouverture < date_end)
        except ValueError:
            pass

    sort = request.args.get("sort", "date_desc")
    sort_map = {
        "client": Client.nom.asc(),
        "titre": Ticket.titre.asc(),
        "type": Ticket.type.asc(),
        "priorite": Ticket.priorite.asc(),
        "etat": Ticket.etat.asc(),
        "date_asc": Ticket.date_ouverture.asc(),
        "date_desc": Ticket.date_ouverture.desc(),
        "materiel": MaterielType.name.asc(),
    }
    order_clause = sort_map.get(sort, sort_map["date_desc"])
    query = query.order_by(order_clause, Ticket.id.desc())

    tickets = query.all()

    clients = Client.query.order_by(Client.nom).all()
    materiel_types = MaterielType.query.order_by(MaterielType.name).all()
    return render_template(
        "tickets.html",
        tickets=tickets,
        clients=clients,
        materiel_types=materiel_types,
        filters=filters,
        sort=sort,
    )


@app.route("/tickets/nouveau", methods=["GET", "POST"])
def nouveau_ticket():
    clients = Client.query.order_by(Client.nom).all()
    materiels = Materiel.query.order_by(Materiel.id).all()
    sites = Site.query.order_by(Site.nom).all()
    categories = MaterielCategory.query.order_by(MaterielCategory.name).all()
    types = MaterielType.query.order_by(MaterielType.name).all()
    users = User.query.order_by(User.full_name).all()

    if request.method == "POST":
        t = Ticket(
            id_client=request.form.get("id_client"),
            category_id=request.form.get("category_id") or None,
            materiel_type_id=request.form.get("materiel_type_id") or None,
            assigned_user_id=request.form.get("assigned_user_id") or None,
            type=request.form.get("type"),
            priorite=request.form.get("priorite"),
            titre=request.form.get("titre"),
            description=request.form.get("description"),
            etat="ouvert"
        )
        db.session.add(t)
        db.session.flush()

        materiels_ids = request.form.getlist("materiels_ids")
        for mid in materiels_ids:
            m = Materiel.query.get(int(mid))
            if m:
                t.materiels.append(m)

        sites_ids = request.form.getlist("sites_ids")
        for sid in sites_ids:
            s = Site.query.get(int(sid))
            if s:
                t.sites.append(s)

        db.session.commit()
        return redirect(url_for("liste_tickets"))

    return render_template(
        "nouveau_ticket.html",
        clients=clients,
        materiels=materiels,
        sites=sites,
        categories=categories,
        types=types,
        users=users,
    )


@app.route("/tickets/<int:id>", methods=["GET", "POST"])
def ticket_fiche(id):
    ticket = Ticket.query.get_or_404(id)

    error_status = None
    if request.method == "POST":
        user = User.query.get(session["user_id"])
        action = request.form.get("action")

        if action == "comment":
            text = request.form.get("content", "").strip()
            if text:
                c = TicketComment(ticket_id=ticket.id, user_id=user.id, content=text)
                db.session.add(c)
                db.session.commit()

        if action == "status":
            new_status = request.form.get("etat")
            ticket.etat = new_status
            if new_status in ("resolu", "cloture"):
                ticket.date_cloture = datetime.now()
            else:
                ticket.date_cloture = None
            # Gestion des crédits contrats
            if new_status in ("resolu", "cloture"):
                client = ticket.client
                # éviter double décompte : check log existant
                already_logged = ContractLog.query.filter_by(ticket_id=ticket.id).first()
                if not already_logged and client.contract_type in ("credit_time", "credit_point"):
                    contract_note = (request.form.get("contract_note") or "").strip()
                    if client.contract_type == "credit_time":
                        duration = request.form.get("duration_hours")
                        start = request.form.get("start_time")
                        end = request.form.get("end_time")
                        hours = None
                        if duration:
                            try:
                                hours = float(duration)
                            except ValueError:
                                hours = None
                        elif start and end:
                            try:
                                fmt = "%H:%M"
                                start_dt = datetime.strptime(start, fmt)
                                end_dt = datetime.strptime(end, fmt)
                                delta = (end_dt - start_dt).total_seconds() / 3600
                                hours = max(delta, 0)
                            except Exception:
                                hours = None
                        if hours is None or hours <= 0:
                            error_status = "Durée invalide pour le crédit temps."
                        else:
                            client.contract_balance = (client.contract_balance or 0) - hours
                            db.session.add(ContractLog(
                                client_id=client.id,
                                ticket_id=ticket.id,
                                kind="credit_time",
                                amount=hours,
                                note=contract_note or f"Ticket #{ticket.id}"
                            ))
                    elif client.contract_type == "credit_point":
                        points = request.form.get("points_used")
                        pts_val = None
                        if points:
                            try:
                                pts_val = float(points)
                            except ValueError:
                                pts_val = None
                        if pts_val is None or pts_val <= 0:
                            error_status = "Nombre d'interventions invalide pour le crédit points."
                        else:
                            client.contract_balance = (client.contract_balance or 0) - pts_val
                            db.session.add(ContractLog(
                                client_id=client.id,
                                ticket_id=ticket.id,
                                kind="credit_point",
                                amount=pts_val,
                                note=contract_note or f"Ticket #{ticket.id}"
                            ))
            if not error_status:
                db.session.commit()

        if action == "edit_comment":
            comment_id = request.form.get("comment_id")
            new_content = request.form.get("content", "").strip()
            comment = TicketComment.query.get_or_404(comment_id)

            # sécurité : on ne modifie que les commentaires du ticket courant
            if comment.ticket_id != ticket.id:
                return redirect(url_for("ticket_fiche", id=id))

            is_admin = user.role == "admin"
            if comment.user_id != user.id and not is_admin:
                return redirect(url_for("ticket_fiche", id=id))

            if new_content and new_content != comment.content:
                comment.previous_content = comment.content
                comment.content = new_content
                comment.updated_at = datetime.now()
                comment.last_editor_id = user.id
                db.session.commit()

        if error_status:
            comments = TicketComment.query.filter_by(ticket_id=id)\
                                          .order_by(TicketComment.created_at.asc()).all()
            is_admin = user.role == "admin"
            edit_diffs = {}
            if is_admin:
                for c in comments:
                    if c.previous_content:
                        diff_lines = difflib.unified_diff(
                            c.previous_content.splitlines(),
                            c.content.splitlines(),
                            fromfile="avant",
                            tofile="apres",
                            lineterm="",
                        )
                        edit_diffs[c.id] = "\n".join(diff_lines)
            contract_logs = ContractLog.query.filter_by(ticket_id=id).order_by(ContractLog.created_at.asc()).all()
            return render_template("ticket_fiche.html", t=ticket, comments=comments, edit_diffs=edit_diffs, is_admin=is_admin, contract_logs=contract_logs, error_status=error_status)

        return redirect(url_for("ticket_fiche", id=id))

    comments = TicketComment.query.filter_by(ticket_id=id)\
                                  .order_by(TicketComment.created_at.asc()).all()

    is_admin = False
    if "user_id" in session:
        current_user = User.query.get(session["user_id"])
        is_admin = current_user.role == "admin"

    edit_diffs = {}
    if is_admin:
        for c in comments:
            if c.previous_content:
                diff_lines = difflib.unified_diff(
                    c.previous_content.splitlines(),
                    c.content.splitlines(),
                    fromfile="avant",
                    tofile="apres",
                    lineterm="",
                )
                edit_diffs[c.id] = "\n".join(diff_lines)

    contract_logs = ContractLog.query.filter_by(ticket_id=id).order_by(ContractLog.created_at.asc()).all()

    if error_status:
        return render_template("ticket_fiche.html", t=ticket, comments=comments, edit_diffs=edit_diffs, is_admin=is_admin, contract_logs=contract_logs, error_status=error_status)

    return render_template("ticket_fiche.html", t=ticket, comments=comments, edit_diffs=edit_diffs, is_admin=is_admin, contract_logs=contract_logs)

@app.route("/tickets/<int:id>/edit", methods=["GET", "POST"])
def ticket_edit(id):
    ticket = Ticket.query.get_or_404(id)
    clients = Client.query.order_by(Client.nom).all()
    materiels = Materiel.query.order_by(Materiel.id).all()
    sites = Site.query.order_by(Site.nom).all()
    categories = MaterielCategory.query.order_by(MaterielCategory.name).all()
    types = MaterielType.query.order_by(MaterielType.name).all()
    users = User.query.order_by(User.full_name).all()

    if request.method == "POST":
        ticket.id_client = request.form.get("id_client")
        ticket.type = request.form.get("type")
        ticket.priorite = request.form.get("priorite")
        ticket.titre = request.form.get("titre")
        ticket.description = request.form.get("description")
        ticket.category_id = request.form.get("category_id") or None
        ticket.materiel_type_id = request.form.get("materiel_type_id") or None
        ticket.assigned_user_id = request.form.get("assigned_user_id") or None

        ticket.materiels.clear()
        materiels_ids = request.form.getlist("materiels_ids")
        for mid in materiels_ids:
            m = Materiel.query.get(int(mid))
            if m:
                ticket.materiels.append(m)

        ticket.sites.clear()
        sites_ids = request.form.getlist("sites_ids")
        for sid in sites_ids:
            s = Site.query.get(int(sid))
            if s:
                ticket.sites.append(s)

        db.session.commit()
        return redirect(url_for("ticket_fiche", id=ticket.id))

    selected_mat_ids = {m.id for m in ticket.materiels}
    selected_site_ids = {s.id for s in ticket.sites}

    return render_template(
        "ticket_edit.html",
        t=ticket,
        clients=clients,
        materiels=materiels,
        sites=sites,
        selected_ids=selected_mat_ids,
        selected_site_ids=selected_site_ids,
        categories=categories,
        types=types,
        users=users,
    )


# ==========================
#  UTILISATEURS / PROFIL
# ==========================
AVAILABLE_ROLES = ("read_only", "technicien", "admin")


@app.route("/users")
def list_users():
    admin = _require_admin()
    if not admin:
        return redirect(url_for("index"))

    users = User.query.order_by(User.id).all()
    return render_template("users.html", users=users, roles=AVAILABLE_ROLES)


@app.route("/users/nouveau", methods=["GET", "POST"])
def new_user():
    admin = _require_admin()
    if not admin:
        return redirect(url_for("index"))

    error = None
    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        login_value = request.form.get("login", "").strip()
        password = request.form.get("password", "")
        role = request.form.get("role", "technicien")

        if not full_name or not login_value or not password:
            error = "Tous les champs sont obligatoires."
        elif role not in AVAILABLE_ROLES:
            error = "Rôle invalide."
        elif User.query.filter_by(login=login_value).first():
            error = "Ce login existe déjà."
        else:
            u = User(
                full_name=full_name,
                login=login_value,
                role=role,
                password_hash=generate_password_hash(password),
            )
            db.session.add(u)
            db.session.commit()
            return redirect(url_for("list_users"))

    return render_template("new_user.html", error=error, roles=AVAILABLE_ROLES)


@app.route("/me/password", methods=["GET", "POST"])
def change_password():
    user = _get_current_user()
    if not user:
        return redirect(url_for("login"))

    error = None
    success = False
    if request.method == "POST":
        old_password = request.form.get("old_password", "")
        new_password = request.form.get("new_password", "")
        new_password_confirm = request.form.get("new_password_confirm", "")

        if not old_password or not new_password or not new_password_confirm:
            error = "Tous les champs sont obligatoires."
        elif not check_password_hash(user.password_hash, old_password):
            error = "Ancien mot de passe incorrect."
        elif new_password != new_password_confirm:
            error = "La confirmation ne correspond pas."
        else:
            user.password_hash = generate_password_hash(new_password)
            db.session.commit()
            success = True

    return render_template("change_password.html", error=error, success=success)


# ==========================
#  RUN
# ==========================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)
