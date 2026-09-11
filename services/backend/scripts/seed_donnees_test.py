"""Bootstrap script : cree un compte de test pret a l'emploi pour chaque partie de la
plateforme (PME, acheteur/donneur d'ordre, partenaire financier), avec des entreprises
deja validees KYC. Complementaire a scripts/seed_admin.py (qui cree le compte admin et la
grille tarifaire par defaut) - executez-le d'abord si l'admin n'existe pas encore.

L'acheteur recoit DEUX comptes (validateur_1 et validateur_2) car la double validation
d'une facture est desormais systematique : il faut toujours les deux roles pour valider
une facture, quel que soit le montant.

Idempotent : peut etre relance sans dupliquer les entreprises/utilisateurs deja crees
(detection par NINEA / telephone).

Usage : docker compose run --rm backend python -m scripts.seed_donnees_test
"""

from datetime import date

from app.database import SessionLocal
from app.models.entreprise import Entreprise
from app.models.enums import RoleUtilisateur, StatutKyc, TypeEntreprise
from app.models.utilisateur import Utilisateur
from app.security import hash_password

MOT_DE_PASSE_TEST = "Test1234!"


def _creer_entreprise_si_absente(
    db,
    *,
    type: TypeEntreprise,
    raison_sociale: str,
    ninea: str,
    secteur_activite: str,
    telephone: str,
    email: str,
    adresse: str,
) -> Entreprise:
    existante = db.query(Entreprise).filter(Entreprise.ninea == ninea).first()
    if existante is not None:
        return existante

    entreprise = Entreprise(
        type=type,
        raison_sociale=raison_sociale,
        ninea=ninea,
        statut_kyc=StatutKyc.VALIDE,
        secteur_activite=secteur_activite,
        date_creation=date.today(),
        contact_telephone=telephone,
        contact_email=email,
        adresse=adresse,
    )
    db.add(entreprise)
    db.flush()
    return entreprise


def _creer_utilisateur_si_absent(
    db,
    *,
    entreprise: Entreprise,
    role: RoleUtilisateur,
    nom: str,
    telephone: str,
    email: str,
) -> Utilisateur:
    existant = db.query(Utilisateur).filter(Utilisateur.telephone == telephone).first()
    if existant is not None:
        return existant

    utilisateur = Utilisateur(
        entreprise_id=entreprise.id,
        role=role,
        nom=nom,
        telephone=telephone,
        email=email,
        mot_de_passe_hash=hash_password(MOT_DE_PASSE_TEST),
    )
    db.add(utilisateur)
    db.flush()
    return utilisateur


def main() -> None:
    db = SessionLocal()
    try:
        pme = _creer_entreprise_si_absente(
            db,
            type=TypeEntreprise.PME,
            raison_sociale="Senegal Fruits SARL",
            ninea="100000001",
            secteur_activite="Agroalimentaire",
            telephone="+221771111100",
            email="contact@senegalfruits.sn",
            adresse="Zone Industrielle, Rue 12, Dakar, Senegal",
        )
        membre_pme = _creer_utilisateur_si_absent(
            db,
            entreprise=pme,
            role=RoleUtilisateur.MEMBRE_PME,
            nom="Fatou Ndiaye",
            telephone="+221771111111",
            email="fatou@senegalfruits.sn",
        )

        acheteur = _creer_entreprise_si_absente(
            db,
            type=TypeEntreprise.GRANDE_ENTREPRISE,
            raison_sociale="Auchan Senegal",
            ninea="100000002",
            secteur_activite="Grande distribution",
            telephone="+221772222200",
            email="contact@auchan.sn",
            adresse="Route de Ouakam, Dakar, Senegal",
        )
        validateur_1 = _creer_utilisateur_si_absent(
            db,
            entreprise=acheteur,
            role=RoleUtilisateur.VALIDATEUR_1,
            nom="Ousmane Diop",
            telephone="+221772222221",
            email="ousmane@auchan.sn",
        )
        validateur_2 = _creer_utilisateur_si_absent(
            db,
            entreprise=acheteur,
            role=RoleUtilisateur.VALIDATEUR_2,
            nom="Aissatou Sow",
            telephone="+221772222222",
            email="aissatou@auchan.sn",
        )

        partenaire = _creer_entreprise_si_absente(
            db,
            type=TypeEntreprise.PARTENAIRE_FINANCIER,
            raison_sociale="Banque Atlantique",
            ninea="100000003",
            secteur_activite="Finance",
            telephone="+221773333300",
            email="contact@banqueatlantique.sn",
            adresse="Avenue Leopold Sedar Senghor, Dakar, Senegal",
        )
        agent_financier = _creer_utilisateur_si_absent(
            db,
            entreprise=partenaire,
            role=RoleUtilisateur.AGENT_FINANCIER,
            nom="Modou Gueye",
            telephone="+221773333333",
            email="modou@banqueatlantique.sn",
        )

        db.commit()

        print("Comptes de test prets (mot de passe pour tous : " + MOT_DE_PASSE_TEST + ") :")
        print(f"  PME (membre_pme)            : {membre_pme.telephone}")
        print(f"  Acheteur (validateur_1)     : {validateur_1.telephone}")
        print(f"  Acheteur (validateur_2)     : {validateur_2.telephone}")
        print(f"  Partenaire (agent_financier): {agent_financier.telephone}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
