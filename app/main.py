import os
from datetime import datetime

from flask import (
    Flask, render_template, request,
    redirect, url_for, session, jsonify
)
import difflib
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

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

class Site(db.Model):
    __tablename__ = "sites"
    id = db.Column(db.Integer, primary_key=True)

    id_client = db.Column(db.Integer, db.ForeignKey("clients.id"), nullable=False)
    nom = db.Column(db.String(128), nullable=False)
    adresse = db.Column(db.String(255), nullable=True)
    ville = db.Column(db.String(128), nullable=True)
    notes = db.Column(db.Text, nullable=True)

    client = db.relationship("Client", backref="sites")


class Materiel(db.Model):
    __tablename__ = "materiels"
    id = db.Column(db.Integer, primary_key=True)

    id_client = db.Column(db.Integer, db.ForeignKey("clients.id"), nullable=False)
    type = db.Column(db.String(64), nullable=False)
    modele = db.Column(db.String(128), nullable=False)
    numero_serie = db.Column(db.String(128), nullable=False)
    date_installation = db.Column(db.String(20), nullable=True)
    garantie_fin = db.Column(db.String(20), nullable=True)
    statut = db.Column(db.String(32), nullable=False, default="en service")

    client = db.relationship("Client", backref="materiels")


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

    titre = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    type = db.Column(db.String(32), nullable=False)
    priorite = db.Column(db.String(16), nullable=False)
    etat = db.Column(db.String(32), nullable=False, default="ouvert")

    date_ouverture = db.Column(db.DateTime, default=datetime.now)
    date_cloture = db.Column(db.DateTime, nullable=True)

    client = db.relationship("Client")

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
    user = db.relationship("User", backref="comments")
    last_editor = db.relationship("User", foreign_keys=[last_editor_id])

    @property
    def is_edited(self):
        return self.updated_at is not None


# ==========================
#  INIT BDD + USER ADMIN
# ==========================
with app.app_context():
    db.create_all()

    admin_login = os.getenv("GMAO_ADMIN_LOGIN")
    admin_name = os.getenv("GMAO_ADMIN_NAME", "Admin")
    admin_password = os.getenv("GMAO_ADMIN_PASSWORD")

    if admin_login and admin_password:
        if not User.query.filter_by(login=admin_login).first():
            u = User(
                full_name=admin_name,
                login=admin_login,
                role="technicien",
                password_hash=generate_password_hash(admin_password),
            )
            db.session.add(u)
            db.session.commit()
            print(f"[GMAO] Utilisateur technicien créé : {admin_login}")


# ==========================
#  HELPERS
# ==========================
@app.context_processor
def inject_user():
    current_user = None
    if "user_id" in session:
        current_user = User.query.get(session["user_id"])
    return dict(current_user=current_user)


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
    clients = Client.query.order_by(Client.id).all()
    return render_template("index.html", clients=clients)


@app.route("/clients/nouveau", methods=["GET", "POST"])
def nouveau_client():
    if request.method == "POST":
        nom = request.form.get("nom", "").strip()
        if not nom:
            return render_template("nouveau_client.html", error="Nom obligatoire")
        db.session.add(Client(nom=nom))
        db.session.commit()
        return redirect(url_for("index"))
    return render_template("nouveau_client.html")
@app.route("/clients/<int:id>/edit", methods=["GET", "POST"])
def edit_client(id):
    client = Client.query.get_or_404(id)

    if request.method == "POST":
        nom = request.form.get("nom", "").strip()
        if not nom:
            return render_template("edit_client.html", client=client, error="Le nom est obligatoire")
        client.nom = nom
        db.session.commit()
        return redirect(url_for("index"))

    return render_template("edit_client.html", client=client)

@app.route("/clients/<int:id>")
def client_fiche(id):
    client = Client.query.get_or_404(id)
    # On peut aussi afficher ses sites, matériels, tickets
    tickets = Ticket.query.filter_by(id_client=id).order_by(Ticket.id.desc()).all()
    materiels = Materiel.query.filter_by(id_client=id).order_by(Materiel.id).all()
    return render_template("client_fiche.html", client=client, tickets=tickets, materiels=materiels)
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
                "label": f"{m.type} {m.modele} ({m.numero_serie})"
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


@app.route("/materiels/nouveau", methods=["GET", "POST"])
def nouveau_materiel():
    clients = Client.query.order_by(Client.nom).all()

    if request.method == "POST":
        m = Materiel(
            id_client=request.form.get("id_client"),
            type=request.form.get("type"),
            modele=request.form.get("modele"),
            numero_serie=request.form.get("numero_serie"),
            date_installation=request.form.get("date_installation"),
            garantie_fin=request.form.get("garantie_fin"),
            statut=request.form.get("statut"),
        )
        db.session.add(m)
        db.session.commit()
        return redirect(url_for("liste_materiels"))

    return render_template("nouveau_materiel.html", clients=clients)


@app.route("/materiels/<int:id>")
def materiel_fiche(id):
    return render_template("materiel_fiche.html", m=Materiel.query.get_or_404(id))
@app.route("/materiels/<int:id>/edit", methods=["GET", "POST"])
def materiel_edit(id):
    materiel = Materiel.query.get_or_404(id)
    clients = Client.query.order_by(Client.nom).all()

    if request.method == "POST":
        materiel.id_client = request.form.get("id_client")
        materiel.type = request.form.get("type")
        materiel.modele = request.form.get("modele")
        materiel.numero_serie = request.form.get("numero_serie")
        materiel.date_installation = request.form.get("date_installation")
        materiel.garantie_fin = request.form.get("garantie_fin")
        materiel.statut = request.form.get("statut")

        db.session.commit()
        return redirect(url_for("materiel_fiche", id=materiel.id))

    return render_template("materiel_edit.html", m=materiel, clients=clients)


# ==========================
#  TICKETS
# ==========================
@app.route("/tickets")
def liste_tickets():
    tickets = Ticket.query.order_by(Ticket.id.desc()).all()
    return render_template("tickets.html", tickets=tickets)


@app.route("/tickets/nouveau", methods=["GET", "POST"])
def nouveau_ticket():
    clients = Client.query.order_by(Client.nom).all()
    materiels = Materiel.query.order_by(Materiel.id).all()
    sites = Site.query.order_by(Site.nom).all()

    if request.method == "POST":
        t = Ticket(
            id_client=request.form.get("id_client"),
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
    )


@app.route("/tickets/<int:id>", methods=["GET", "POST"])
def ticket_fiche(id):
    ticket = Ticket.query.get_or_404(id)

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

    return render_template("ticket_fiche.html", t=ticket, comments=comments, edit_diffs=edit_diffs, is_admin=is_admin)

@app.route("/tickets/<int:id>/edit", methods=["GET", "POST"])
def ticket_edit(id):
    ticket = Ticket.query.get_or_404(id)
    clients = Client.query.order_by(Client.nom).all()
    materiels = Materiel.query.order_by(Materiel.id).all()
    sites = Site.query.order_by(Site.nom).all()

    if request.method == "POST":
        ticket.id_client = request.form.get("id_client")
        ticket.type = request.form.get("type")
        ticket.priorite = request.form.get("priorite")
        ticket.titre = request.form.get("titre")
        ticket.description = request.form.get("description")

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
    )

# ==========================
#  RUN
# ==========================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)
