# 🏠 SenImmo — Backend Flask + Frontend HTML

Plateforme immobilière complète pour le Sénégal.  
**Backend** : Python / Flask / SQLite  
**Frontend** : HTML + CSS + JavaScript (vanilla)

---

## ⚡ Démarrage rapide (3 étapes)

### 1. Installer les dépendances

```bash
pip install flask flask-cors
```

### 2. Lancer le serveur

```bash
python app.py
```

Vous verrez dans le terminal :
```
══════════════════════════════════════════════════
  🏠  SenImmo — Backend Flask
  📦  Initialisation de la base de données…
  ✅  Base de données prête : senimmo.db
  🚀  Serveur démarré → http://localhost:5000
  🔑  Admin : admin@senimmo.sn / admin123
══════════════════════════════════════════════════
```

### 3. Ouvrir le site

Ouvrez votre navigateur sur **http://localhost:5000**

---

## 🔑 Compte administrateur par défaut

| Champ       | Valeur              |
|-------------|---------------------|
| Email       | admin@senimmo.sn    |
| Mot de passe | admin123           |

---

## 📁 Structure du projet

```
senimmo/
├── app.py                  ← Serveur Flask (backend)
├── requirements.txt        ← Dépendances Python
├── senimmo.db              ← Base de données SQLite (créée auto)
├── templates/
│   └── index.html          ← Interface du site (frontend)
└── static/
    └── uploads/            ← Images uploadées par l'admin
```

---

## 🔌 API — Endpoints disponibles

### Authentification
| Méthode | URL                  | Description                  |
|---------|----------------------|------------------------------|
| POST    | `/api/connexion`     | Connexion admin              |
| POST    | `/api/deconnexion`   | Déconnexion                  |
| GET     | `/api/session`       | Vérifie la session active    |

### Biens immobiliers
| Méthode | URL                       | Description                         |
|---------|---------------------------|-------------------------------------|
| GET     | `/api/biens`              | Liste tous les biens (avec filtres) |
| GET     | `/api/biens?type=villa`   | Filtrer par type                    |
| GET     | `/api/biens?operation=louer` | Filtrer par opération            |
| GET     | `/api/biens?q=dakar`      | Recherche par mot-clé               |
| GET     | `/api/biens/42`           | Détail d'un bien                    |
| POST    | `/api/biens`              | Créer un bien (admin requis)        |
| PUT     | `/api/biens/42`           | Modifier un bien (admin requis)     |
| DELETE  | `/api/biens/42`           | Supprimer un bien (admin requis)    |

### Images
| Méthode | URL                          | Description                    |
|---------|------------------------------|--------------------------------|
| POST    | `/api/biens/42/images`       | Uploader une image (admin)     |
| DELETE  | `/api/images/7`              | Supprimer une image (admin)    |

### Contact
| Méthode | URL                      | Description                |
|---------|--------------------------|----------------------------|
| POST    | `/api/contact`           | Envoyer un message         |
| GET     | `/api/messages`          | Voir les messages (admin)  |
| PUT     | `/api/messages/3/lu`     | Marquer un message comme lu|

### Statistiques
| Méthode | URL          | Description               |
|---------|--------------|---------------------------|
| GET     | `/api/stats` | Chiffres du tableau de bord|

---

## 🛡️ Déploiement en production

Pour mettre en ligne, remplacez Flask dev par **Gunicorn** :

```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

Et changez `app.secret_key` dans `app.py` par une clé secrète aléatoire.

---

## 🗄️ Base de données SQLite

Le fichier `senimmo.db` est créé automatiquement au premier lancement.  
Pour l'explorer visuellement : [DB Browser for SQLite](https://sqlitebrowser.org/) (gratuit).

Tables :
- `utilisateurs` — Comptes admin
- `biens` — Biens immobiliers
- `images` — Images associées aux biens
- `messages` — Messages de contact
