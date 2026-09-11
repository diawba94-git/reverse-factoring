# Démarrage — Cedra

## 1. Lancer la stack

```bash
docker compose up -d
docker compose run --rm backend alembic upgrade head
docker compose run --rm backend python -m scripts.seed_admin
docker compose run --rm backend python -m scripts.seed_donnees_test
```

- API + Swagger UI : http://localhost:8000/docs
- Frontend web (Cedra) : http://localhost:5175
- Plan de test manuel détaillé (cycle complet) : [manual-tests.http](manual-tests.http)

Les deux scripts `seed_*` sont idempotents : les relancer ne duplique rien (détection par
NINEA / téléphone).

## 2. Comptes de test

Mot de passe commun à tous les comptes de test (hors admin) : **`Test1234!`**

| Partie                          | Entreprise           | Nom            | Téléphone       | Rôle             | Mot de passe     |
|----------------------------------|-----------------------|----------------|-----------------|------------------|-------------------|
| Admin (équipe Cedra)             | InvoiceUp Plateforme  | Administrateur Cedra | `+221770000000` | `admin`           | `ChangeMoi123!`   |
| PME (fournisseur)                | Senegal Fruits SARL   | Fatou Ndiaye   | `+221771111111` | `membre_pme`      | `Test1234!`       |
| Acheteur (donneur d'ordre) — validateur 1 | Auchan Senegal | Ousmane Diop | `+221772222221` | `validateur_1`    | `Test1234!`       |
| Acheteur (donneur d'ordre) — validateur 2 | Auchan Senegal | Aissatou Sow | `+221772222222` | `validateur_2`    | `Test1234!`       |
| Partenaire financier             | Banque Atlantique     | Modou Gueye    | `+221773333333` | `agent_financier` | `Test1234!`       |

**Pourquoi deux comptes acheteur ?** La double validation d'une facture est systématique
et sans seuil de montant : il faut toujours une validation `validateur_1` **et** une
validation `validateur_2` de la même entreprise donneur d'ordre (dans n'importe quel
ordre) avant qu'une facture ne passe à `validee`. Les deux comptes de test permettent de
dérouler ce cycle complet.

Toutes les entreprises créées par `seed_donnees_test` démarrent avec un statut KYC déjà
`valide` (contrairement à une inscription en libre-service normale, qui démarre en
`en_attente`), pour être immédiatement utilisables — y compris pour tester le système
d'invitation (`POST /entreprises/{id}/inviter`), qui exige une entreprise déjà validée.

## 3. Se connecter

- Via Swagger UI : `POST /auth/login` avec `{"identifiant": "...", "mot_de_passe": "..."}`
  (`identifiant` accepte indifféremment le téléphone ou l'email du compte),
  puis "Authorize" avec le `access_token` reçu.
- Via le frontend web (http://localhost:5175) : écran de connexion standard.
- Via le fichier [manual-tests.http](manual-tests.http) (extension VS Code "REST Client") :
  reprend déjà tout le cycle facture → double validation → avance → remboursement.

## 4. Réinitialiser les données

Pour repartir d'une base vierge (tout est perdu, y compris les comptes de test) :

```bash
docker compose down -v
docker compose up -d
docker compose run --rm backend alembic upgrade head
docker compose run --rm backend python -m scripts.seed_admin
docker compose run --rm backend python -m scripts.seed_donnees_test
```
