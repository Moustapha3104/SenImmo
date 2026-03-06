"""
╔══════════════════════════════════════════════════════╗
║         SenImmo — Backend Flask (Python)             ║
║         Base de données : SQLite (intégrée)          ║
║         Langage : Python 3 + Flask                   ║
╚══════════════════════════════════════════════════════╝

Installation rapide :
    pip install flask flask-cors
    python app.py
    → Ouvrez http://localhost:5000
"""

from flask import Flask, request, jsonify, send_from_directory, session
from flask_cors import CORS
import sqlite3
import os
import json
import hashlib
import uuid
from datetime import datetime

# ─────────────────────────────────────────────
#  CONFIGURATION
# ─────────────────────────────────────────────
app = Flask(__name__, static_folder="static", template_folder="templates")
app.secret_key = "senimmo_secret_2026"   # Changez en production !
CORS(app, supports_credentials=True)

BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
DB_PATH    = os.path.join(BASE_DIR, "senimmo.db")
UPLOAD_DIR = os.path.join(BASE_DIR, "static", "uploads")
ALLOWED    = {"png", "jpg", "jpeg", "webp", "gif"}
MAX_SIZE   = 10 * 1024 * 1024   # 10 Mo

os.makedirs(UPLOAD_DIR, exist_ok=True)


# ─────────────────────────────────────────────
#  BASE DE DONNÉES  (SQLite — fichier local)
# ─────────────────────────────────────────────
def get_db():
    """Retourne une connexion à la base SQLite."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row   # Résultats accessibles comme dict
    return conn


def init_db():
    """Crée les tables si elles n'existent pas encore."""
    with get_db() as db:
        db.executescript("""
            -- ── Table des utilisateurs (admin) ──
            CREATE TABLE IF NOT EXISTS utilisateurs (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                nom       TEXT    NOT NULL,
                email     TEXT    NOT NULL UNIQUE,
                mot_passe TEXT    NOT NULL,        -- hashé en SHA-256
                role      TEXT    DEFAULT 'admin',
                cree_le   TEXT    DEFAULT (datetime('now'))
            );

            -- ── Table des biens immobiliers ──
            CREATE TABLE IF NOT EXISTS biens (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                titre       TEXT    NOT NULL,
                type        TEXT    NOT NULL,       -- maison / appartement / villa
                localisation TEXT  NOT NULL,
                operation   TEXT    NOT NULL,       -- vendre / louer
                prix        TEXT    NOT NULL,
                surface     REAL,
                chambres    INTEGER,
                salles_bain INTEGER,
                description TEXT,
                premium     INTEGER DEFAULT 0,      -- 0 = non, 1 = oui
                actif       INTEGER DEFAULT 1,
                cree_le     TEXT    DEFAULT (datetime('now')),
                modifie_le  TEXT    DEFAULT (datetime('now'))
            );

            -- ── Table des images liées aux biens ──
            CREATE TABLE IF NOT EXISTS images (
                id       INTEGER PRIMARY KEY AUTOINCREMENT,
                bien_id  INTEGER NOT NULL REFERENCES biens(id) ON DELETE CASCADE,
                fichier  TEXT    NOT NULL,          -- nom du fichier dans /static/uploads
                principale INTEGER DEFAULT 0        -- 1 = image de couverture
            );

            -- ── Table des messages de contact ──
            CREATE TABLE IF NOT EXISTS messages (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                prenom    TEXT,
                nom       TEXT,
                email     TEXT,
                telephone TEXT,
                sujet     TEXT,
                contenu   TEXT,
                lu        INTEGER DEFAULT 0,
                recu_le   TEXT DEFAULT (datetime('now'))
            );
        """)

        # ── Compte admin par défaut ──────────────────────
        # Email : admin@senimmo.sn  |  Mot de passe : admin123
        mdp_hash = hashlib.sha256("admin123".encode()).hexdigest()
        db.execute("""
            INSERT OR IGNORE INTO utilisateurs (nom, email, mot_passe, role)
            VALUES ('Administrateur', 'admin@senimmo.sn', ?, 'admin')
        """, (mdp_hash,))

        # ── Biens de démonstration ───────────────────────
        demo = [
            ("Villa Prestige – Almadies",   "villa",       "Almadies, Dakar",    "vendre", "185 000 000", 350, 5, 3, "Magnifique villa contemporaine avec piscine et vue mer.", 1),
            ("Appartement Moderne – Plateau","appartement", "Plateau, Dakar",     "louer",  "450 000",      95, 3, 2, "Bel appartement rénové au cœur du Plateau.", 0),
            ("Maison Familiale – Liberté 6", "maison",      "Liberté 6, Dakar",   "vendre", "65 000 000",  200, 4, 2, "Grande maison dans une cité résidentielle calme.", 0),
            ("Villa Bord de Mer – Saly",     "villa",       "Saly, Mbour",        "louer",  "1 200 000",   280, 5, 4, "Villa luxueuse en front de mer, piscine chauffée.", 1),
            ("Studio Meublé – Mermoz",       "appartement", "Mermoz, Dakar",      "louer",  "180 000",      38, 1, 1, "Studio meublé, climatisé, sécurisé.", 0),
            ("Maison Coloniale – Saint-Louis","maison",      "Île Saint-Louis",    "vendre", "28 000 000",  160, 3, 2, "Maison coloniale restaurée, patrimoine UNESCO.", 0),
        ]
        for b in demo:
            db.execute("""
                INSERT OR IGNORE INTO biens
                  (titre, type, localisation, operation, prix, surface, chambres, salles_bain, description, premium)
                VALUES (?,?,?,?,?,?,?,?,?,?)
            """, b)
        db.commit()


# ─────────────────────────────────────────────
#  UTILITAIRES
# ─────────────────────────────────────────────
def hash_mdp(mdp: str) -> str:
    return hashlib.sha256(mdp.encode()).hexdigest()


def extension_ok(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED


def bien_vers_dict(bien, images) -> dict:
    """Convertit une ligne SQLite + liste d'images en dictionnaire JSON-sérialisable."""
    d = dict(bien)
    d["images"] = [
        {"id": img["id"], "url": f"/static/uploads/{img['fichier']}", "principale": img["principale"]}
        for img in images
    ]
    # Image de couverture par défaut si aucune image uploadée
    if not d["images"]:
        d["images"] = [{"id": 0, "url": "/static/placeholder.jpg", "principale": 1}]
    return d


def login_requis(f):
    """Décorateur — redirige si l'utilisateur n'est pas connecté."""
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            return jsonify({"erreur": "Non autorisé. Veuillez vous connecter."}), 401
        return f(*args, **kwargs)
    return decorated


# ─────────────────────────────────────────────
#  ROUTES — PAGES
# ─────────────────────────────────────────────
@app.route("/")
def index():
    """Sert le fichier HTML principal du site."""
    return send_from_directory("templates", "index.html")


# ─────────────────────────────────────────────
#  ROUTES — AUTHENTIFICATION
# ─────────────────────────────────────────────
@app.route("/api/connexion", methods=["POST"])
def connexion():
    """
    POST /api/connexion
    Body JSON : { "email": "...", "mot_passe": "..." }
    Retourne   : { "succes": true, "utilisateur": {...} }
    """
    data = request.get_json()
    if not data:
        return jsonify({"erreur": "Données manquantes"}), 400

    email   = data.get("email", "").strip().lower()
    mot_passe = data.get("mot_passe", "")

    with get_db() as db:
        user = db.execute(
            "SELECT * FROM utilisateurs WHERE email = ? AND mot_passe = ?",
            (email, hash_mdp(mot_passe))
        ).fetchone()

    if not user:
        return jsonify({"erreur": "Email ou mot de passe incorrect"}), 401

    session["user_id"] = user["id"]
    session["nom"]     = user["nom"]
    session["role"]    = user["role"]

    return jsonify({
        "succes": True,
        "utilisateur": {"id": user["id"], "nom": user["nom"], "email": user["email"], "role": user["role"]}
    })


@app.route("/api/deconnexion", methods=["POST"])
def deconnexion():
    """POST /api/deconnexion — Supprime la session."""
    session.clear()
    return jsonify({"succes": True, "message": "Déconnecté avec succès"})


@app.route("/api/session", methods=["GET"])
def check_session():
    """GET /api/session — Vérifie si l'utilisateur est connecté."""
    if "user_id" in session:
        return jsonify({"connecte": True, "nom": session.get("nom"), "role": session.get("role")})
    return jsonify({"connecte": False})


# ─────────────────────────────────────────────
#  ROUTES — BIENS IMMOBILIERS
# ─────────────────────────────────────────────
@app.route("/api/biens", methods=["GET"])
def liste_biens():
    """
    GET /api/biens?type=villa&operation=vendre&q=dakar
    Retourne la liste de tous les biens actifs (avec filtres optionnels).
    """
    type_filtre = request.args.get("type", "")
    op_filtre   = request.args.get("operation", "")
    recherche   = request.args.get("q", "")

    requete = "SELECT * FROM biens WHERE actif = 1"
    params  = []

    if type_filtre:
        requete += " AND type = ?"
        params.append(type_filtre)
    if op_filtre:
        requete += " AND operation = ?"
        params.append(op_filtre)
    if recherche:
        requete += " AND (titre LIKE ? OR localisation LIKE ? OR description LIKE ?)"
        params += [f"%{recherche}%"] * 3

    requete += " ORDER BY premium DESC, cree_le DESC"

    with get_db() as db:
        biens = db.execute(requete, params).fetchall()
        resultat = []
        for bien in biens:
            images = db.execute("SELECT * FROM images WHERE bien_id = ?", (bien["id"],)).fetchall()
            resultat.append(bien_vers_dict(bien, images))

    return jsonify({"biens": resultat, "total": len(resultat)})


@app.route("/api/biens/<int:bien_id>", methods=["GET"])
def detail_bien(bien_id):
    """GET /api/biens/42 — Retourne les détails d'un bien."""
    with get_db() as db:
        bien = db.execute("SELECT * FROM biens WHERE id = ? AND actif = 1", (bien_id,)).fetchone()
        if not bien:
            return jsonify({"erreur": "Bien introuvable"}), 404
        images = db.execute("SELECT * FROM images WHERE bien_id = ?", (bien_id,)).fetchall()
    return jsonify(bien_vers_dict(bien, images))


@app.route("/api/biens", methods=["POST"])
@login_requis
def creer_bien():
    """
    POST /api/biens  (admin requis)
    Body JSON : { titre, type, localisation, operation, prix,
                  surface, chambres, salles_bain, description, premium }
    """
    data = request.get_json()
    if not data:
        return jsonify({"erreur": "Données manquantes"}), 400

    champs_requis = ["titre", "type", "localisation", "operation", "prix"]
    for c in champs_requis:
        if not data.get(c):
            return jsonify({"erreur": f"Champ requis manquant : {c}"}), 400

    with get_db() as db:
        cursor = db.execute("""
            INSERT INTO biens
              (titre, type, localisation, operation, prix, surface,
               chambres, salles_bain, description, premium)
            VALUES (?,?,?,?,?,?,?,?,?,?)
        """, (
            data["titre"],
            data["type"],
            data["localisation"],
            data["operation"],
            data["prix"],
            data.get("surface"),
            data.get("chambres"),
            data.get("salles_bain"),
            data.get("description", ""),
            1 if data.get("premium") else 0
        ))
        db.commit()
        nouveau_id = cursor.lastrowid

    return jsonify({"succes": True, "id": nouveau_id, "message": "Bien créé avec succès"}), 201


@app.route("/api/biens/<int:bien_id>", methods=["PUT"])
@login_requis
def modifier_bien(bien_id):
    """PUT /api/biens/42  (admin requis) — Modifie un bien existant."""
    data = request.get_json()
    if not data:
        return jsonify({"erreur": "Données manquantes"}), 400

    with get_db() as db:
        bien = db.execute("SELECT id FROM biens WHERE id = ?", (bien_id,)).fetchone()
        if not bien:
            return jsonify({"erreur": "Bien introuvable"}), 404

        db.execute("""
            UPDATE biens
            SET titre=?, type=?, localisation=?, operation=?, prix=?,
                surface=?, chambres=?, salles_bain=?, description=?,
                premium=?, modifie_le=datetime('now')
            WHERE id=?
        """, (
            data.get("titre"),
            data.get("type"),
            data.get("localisation"),
            data.get("operation"),
            data.get("prix"),
            data.get("surface"),
            data.get("chambres"),
            data.get("salles_bain"),
            data.get("description"),
            1 if data.get("premium") else 0,
            bien_id
        ))
        db.commit()

    return jsonify({"succes": True, "message": "Bien modifié avec succès"})


@app.route("/api/biens/<int:bien_id>", methods=["DELETE"])
@login_requis
def supprimer_bien(bien_id):
    """DELETE /api/biens/42  (admin requis) — Désactive un bien (soft delete)."""
    with get_db() as db:
        bien = db.execute("SELECT id FROM biens WHERE id = ?", (bien_id,)).fetchone()
        if not bien:
            return jsonify({"erreur": "Bien introuvable"}), 404
        db.execute("UPDATE biens SET actif = 0 WHERE id = ?", (bien_id,))
        db.commit()

    return jsonify({"succes": True, "message": "Bien supprimé"})


# ─────────────────────────────────────────────
#  ROUTES — UPLOAD D'IMAGES
# ─────────────────────────────────────────────
@app.route("/api/biens/<int:bien_id>/images", methods=["POST"])
@login_requis
def upload_image(bien_id):
    """
    POST /api/biens/42/images  (admin requis)
    Form-data : fichier = <image>
    Sauvegarde l'image dans /static/uploads/ et enregistre en base.
    """
    if "fichier" not in request.files:
        return jsonify({"erreur": "Aucun fichier envoyé"}), 400

    fichier = request.files["fichier"]

    if fichier.filename == "":
        return jsonify({"erreur": "Nom de fichier vide"}), 400

    if not extension_ok(fichier.filename):
        return jsonify({"erreur": "Format non autorisé (jpg, png, webp uniquement)"}), 400

    # Vérifie la taille
    fichier.seek(0, 2)
    if fichier.tell() > MAX_SIZE:
        return jsonify({"erreur": "Fichier trop volumineux (max 10 Mo)"}), 400
    fichier.seek(0)

    # Nom unique pour éviter les conflits
    ext        = fichier.filename.rsplit(".", 1)[1].lower()
    nom_unique = f"{uuid.uuid4().hex}.{ext}"
    chemin     = os.path.join(UPLOAD_DIR, nom_unique)
    fichier.save(chemin)

    with get_db() as db:
        # Première image = principale automatiquement
        nb_images = db.execute("SELECT COUNT(*) FROM images WHERE bien_id=?", (bien_id,)).fetchone()[0]
        principale = 1 if nb_images == 0 else 0
        db.execute(
            "INSERT INTO images (bien_id, fichier, principale) VALUES (?,?,?)",
            (bien_id, nom_unique, principale)
        )
        db.commit()

    return jsonify({
        "succes": True,
        "fichier": nom_unique,
        "url": f"/static/uploads/{nom_unique}"
    }), 201


@app.route("/api/images/<int:image_id>", methods=["DELETE"])
@login_requis
def supprimer_image(image_id):
    """DELETE /api/images/7  (admin requis) — Supprime une image."""
    with get_db() as db:
        img = db.execute("SELECT * FROM images WHERE id=?", (image_id,)).fetchone()
        if not img:
            return jsonify({"erreur": "Image introuvable"}), 404

        chemin = os.path.join(UPLOAD_DIR, img["fichier"])
        if os.path.exists(chemin):
            os.remove(chemin)

        db.execute("DELETE FROM images WHERE id=?", (image_id,))
        db.commit()

    return jsonify({"succes": True, "message": "Image supprimée"})


# ─────────────────────────────────────────────
#  ROUTES — MESSAGES DE CONTACT
# ─────────────────────────────────────────────
@app.route("/api/contact", methods=["POST"])
def envoyer_message():
    """
    POST /api/contact
    Body JSON : { prenom, nom, email, telephone, sujet, contenu }
    """
    data = request.get_json()
    if not data or not data.get("email") or not data.get("contenu"):
        return jsonify({"erreur": "Email et message requis"}), 400

    with get_db() as db:
        db.execute("""
            INSERT INTO messages (prenom, nom, email, telephone, sujet, contenu)
            VALUES (?,?,?,?,?,?)
        """, (
            data.get("prenom", ""),
            data.get("nom", ""),
            data.get("email", ""),
            data.get("telephone", ""),
            data.get("sujet", ""),
            data.get("contenu", "")
        ))
        db.commit()

    return jsonify({"succes": True, "message": "Message reçu, nous vous répondrons sous 24h !"}), 201


@app.route("/api/messages", methods=["GET"])
@login_requis
def liste_messages():
    """GET /api/messages  (admin requis) — Liste tous les messages."""
    with get_db() as db:
        msgs = db.execute("SELECT * FROM messages ORDER BY recu_le DESC").fetchall()
    return jsonify({"messages": [dict(m) for m in msgs], "total": len(msgs)})


@app.route("/api/messages/<int:msg_id>/lu", methods=["PUT"])
@login_requis
def marquer_lu(msg_id):
    """PUT /api/messages/3/lu  (admin) — Marque un message comme lu."""
    with get_db() as db:
        db.execute("UPDATE messages SET lu=1 WHERE id=?", (msg_id,))
        db.commit()
    return jsonify({"succes": True})


# ─────────────────────────────────────────────
#  ROUTES — STATISTIQUES (Admin)
# ─────────────────────────────────────────────
@app.route("/api/stats", methods=["GET"])
@login_requis
def statistiques():
    """GET /api/stats  (admin) — Tableau de bord en chiffres."""
    with get_db() as db:
        total      = db.execute("SELECT COUNT(*) FROM biens WHERE actif=1").fetchone()[0]
        a_vendre   = db.execute("SELECT COUNT(*) FROM biens WHERE actif=1 AND operation='vendre'").fetchone()[0]
        a_louer    = db.execute("SELECT COUNT(*) FROM biens WHERE actif=1 AND operation='louer'").fetchone()[0]
        messages   = db.execute("SELECT COUNT(*) FROM messages").fetchone()[0]
        non_lus    = db.execute("SELECT COUNT(*) FROM messages WHERE lu=0").fetchone()[0]

    return jsonify({
        "total_biens":  total,
        "a_vendre":     a_vendre,
        "a_louer":      a_louer,
        "messages":     messages,
        "non_lus":      non_lus
    })


# ─────────────────────────────────────────────
#  DÉMARRAGE
# ─────────────────────────────────────────────
if __name__ == "__main__":
    print("═" * 50)
    print("  🏠  SenImmo — Backend Flask")
    print("  📦  Initialisation de la base de données…")
    init_db()
    print("  ✅  Base de données prête : senimmo.db")
    print("  🚀  Serveur démarré → http://localhost:5000")
    print("  🔑  Admin : admin@senimmo.sn / admin123")
    print("═" * 50)
    app.run(debug=True, host="0.0.0.0", port=5000)
