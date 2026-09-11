import io
import uuid

from app.models.enums import RoleUtilisateur, TypeEntreprise
from app.models.relation_pme_donneur_ordre import RelationPmeDonneurOrdre, ValidateurRelation

from .factories import auth_headers, creer_entreprise, creer_utilisateur


def _admin(db):
    entreprise_admin = creer_entreprise(db, type=TypeEntreprise.PME, raison_sociale="InvoiceUp Plateforme")
    return creer_utilisateur(db, entreprise=entreprise_admin, role=RoleUtilisateur.ADMIN)


def test_parcours_complet_onboarding_acheteur(client, db_session):
    pme = creer_entreprise(db_session, type=TypeEntreprise.PME, raison_sociale="Sénégal Services SARL")
    membre = creer_utilisateur(db_session, entreprise=pme, role=RoleUtilisateur.MEMBRE_PME)

    fiche = client.post(
        "/entreprises/fiche-minimale",
        json={
            "raison_sociale": "CFAO Distribution",
            "contact_invitation_nom": "Moussa Ndiaye",
            "contact_invitation_email": f"moussa.ndiaye+{uuid.uuid4().hex[:10]}@cfao.sn",
        },
        headers=auth_headers(membre),
    ).json()
    token = fiche["token_invitation"]
    assert token

    # 1. Le contact invite rejoint comme validateur_1
    rejoint = client.post(
        f"/auth/rejoindre-entreprise/{token}",
        json={"nom": "Moussa Ndiaye", "telephone": f"+2217{uuid.uuid4().int % 10**8:08d}", "mot_de_passe": "MotDePasse123!"},
    )
    assert rejoint.status_code == 200, rejoint.text
    validateur_1_token = rejoint.json()["access_token"]

    relation = (
        db_session.query(RelationPmeDonneurOrdre)
        .filter(RelationPmeDonneurOrdre.pme_id == pme.id, RelationPmeDonneurOrdre.donneur_ordre_id == fiche["id"])
        .first()
    )
    assert relation is not None
    assert relation.statut.value == "pilote"

    # Le jeton est a usage unique
    rejoint_bis = client.post(
        f"/auth/rejoindre-entreprise/{token}",
        json={"nom": "Autre Personne", "telephone": f"+2217{uuid.uuid4().int % 10**8:08d}", "mot_de_passe": "MotDePasse123!"},
    )
    assert rejoint_bis.status_code == 404

    # 2. KYC refusee tant que le second validateur n'existe pas
    kyc_sans_v2 = client.post(
        f"/entreprises/{fiche['id']}/kyc",
        files={"fichier": ("piece.jpg", io.BytesIO(b"x"), "image/jpeg")},
        headers={"Authorization": f"Bearer {validateur_1_token}"},
    )
    assert kyc_sans_v2.status_code == 422, kyc_sans_v2.text

    # 3. validateur_1 invite un validateur_2 (autorise malgre KYC non valide, car pre_inscrite)
    invitation = client.post(
        f"/entreprises/{fiche['id']}/inviter",
        json={
            "telephone": f"+2217{uuid.uuid4().int % 10**8:08d}",
            "email": "aida.sow@cfao.sn",
            "nom": "Aïda Sow",
            "role": "validateur_2",
        },
        headers={"Authorization": f"Bearer {validateur_1_token}"},
    )
    assert invitation.status_code == 201, invitation.text
    token_v2 = invitation.json()["token"]

    accepte = client.post(f"/auth/accepter-invitation/{token_v2}", json={"mot_de_passe": "MotDePasse123!"})
    assert accepte.status_code == 200, accepte.text

    # Le validateur_2 herite de la meme affectation de relation que validateur_1
    utilisateur_v2_id = invitation.json()["utilisateur_id"]
    affectations = (
        db_session.query(ValidateurRelation)
        .filter(ValidateurRelation.relation_id == relation.id)
        .all()
    )
    utilisateurs_affectes = {str(a.utilisateur_id) for a in affectations}
    assert utilisateur_v2_id in utilisateurs_affectes

    # 4. KYC acceptee une fois les deux validateurs presents (et la forme juridique connue,
    # deja exigee par ailleurs par cette route independamment de l'onboarding)
    from app.models.entreprise import Entreprise
    from app.models.enums import FormeJuridique

    import uuid as uuid_module

    entreprise_db = db_session.get(Entreprise, uuid_module.UUID(fiche["id"]))
    entreprise_db.forme_juridique = FormeJuridique.SARL
    db_session.commit()

    kyc_ok = client.post(
        f"/entreprises/{fiche['id']}/kyc",
        files={"fichier": ("piece.jpg", io.BytesIO(b"x"), "image/jpeg")},
        headers={"Authorization": f"Bearer {validateur_1_token}"},
    )
    assert kyc_ok.status_code == 200, kyc_ok.text


def test_resume_relations(client, db_session):
    admin = _admin(db_session)
    pme = creer_entreprise(db_session, type=TypeEntreprise.PME)
    acheteur = creer_entreprise(db_session, type=TypeEntreprise.GRANDE_ENTREPRISE)
    relation = RelationPmeDonneurOrdre(pme_id=pme.id, donneur_ordre_id=acheteur.id)
    db_session.add(relation)
    db_session.commit()

    r = client.get("/relations/resume", headers=auth_headers(admin))
    assert r.status_code == 200, r.text
    assert r.json()["pilote"] >= 1
