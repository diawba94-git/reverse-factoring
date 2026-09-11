"""Bootstrap script : cree le tout premier compte admin et une grille tarifaire par
defaut. A executer une seule fois apres les migrations, tant qu'aucun admin n'existe
(le seul moyen de creer un admin normalement est /utilisateurs, qui exige deja d'etre
authentifie en tant qu'admin).

Usage : docker compose run --rm backend python -m scripts.seed_admin
"""

from datetime import date
from decimal import Decimal

from app.database import SessionLocal
from app.models.entreprise import Entreprise
from app.models.enums import RoleUtilisateur, StatutKyc, TypeEntreprise
from app.models.grille_tarifaire import GrilleTarifaire
from app.models.utilisateur import Utilisateur
from app.security import hash_password

ADMIN_TELEPHONE = "+221770000000"
ADMIN_MOT_DE_PASSE = "ChangeMoi123!"


def main() -> None:
    db = SessionLocal()
    try:
        if db.query(Utilisateur).filter(Utilisateur.role == RoleUtilisateur.ADMIN).first():
            print("Un admin existe deja, rien a faire.")
        else:
            entreprise_plateforme = Entreprise(
                type=TypeEntreprise.PME,
                raison_sociale="InvoiceUp Plateforme",
                ninea="000000000",
                rccm="SN-DKR-0000-B-00000",
                statut_kyc=StatutKyc.VALIDE,
                secteur_activite="Technologies financieres",
                date_creation=date.today(),
                contact_telephone=ADMIN_TELEPHONE,
                contact_email="admin@invoiceup.local",
                adresse="Dakar, Senegal",
            )
            db.add(entreprise_plateforme)
            db.flush()

            admin = Utilisateur(
                entreprise_id=entreprise_plateforme.id,
                role=RoleUtilisateur.ADMIN,
                nom="Administrateur Cedra",
                telephone=ADMIN_TELEPHONE,
                email="admin@invoiceup.local",
                mot_de_passe_hash=hash_password(ADMIN_MOT_DE_PASSE),
            )
            db.add(admin)
            db.commit()
            print(f"Admin cree : telephone={ADMIN_TELEPHONE} mot_de_passe={ADMIN_MOT_DE_PASSE}")

        if not db.query(GrilleTarifaire).filter(GrilleTarifaire.active.is_(True)).first():
            grille = GrilleTarifaire(
                nom="Standard — 60-90j",
                taux_total_minimum=Decimal("0.023"),
                taux_total_maximum=Decimal("0.03"),
                proportion_cedra=Decimal("0.3333"),
                proportion_partenaire=Decimal("0.6667"),
                plafond_montant=None,
                duree_minimum_jours=60,
                duree_maximum_jours=90,
                taux_avance=Decimal("0.80"),
                active=True,
                date_debut_validite=date.today(),
            )
            db.add(grille)
            db.commit()
            print("Grille tarifaire par defaut creee : Grille standard")
        else:
            print("Une grille tarifaire active existe deja, rien a faire.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
