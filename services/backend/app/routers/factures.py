import io
import shutil
import uuid
from datetime import date
from decimal import Decimal
from pathlib import Path

import pandas as pd
from fastapi import APIRouter, Depends, Form, HTTPException, Response, UploadFile, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user, require_role
from app.models.entreprise import Entreprise
from app.models.enums import (
    RoleUtilisateur,
    RoleValidateur,
    SourceCreationFacture,
    StatutFacture,
    StatutFiche,
    TypeEntreprise,
)
from app.models.facture import Facture
from app.models.ligne_facture import LigneFacture
from app.models.utilisateur import Utilisateur
from app.models.validation_facture import ValidationFacture
from app.schemas.facture import (
    FactureExtractionOut,
    FactureImportRapport,
    FactureLignesUpdateRequest,
    FactureNativeCreate,
    FactureOut,
    FactureRejetRequest,
    FactureValiderRequest,
    ImportLigneResultat,
    LigneFactureExtraiteOut,
    PremiereValidationInfo,
)
from app.services.audit import enregistrer_audit
from app.services.conformite_facture import ResultatConformite, verifier_conformite_facture
from app.services.extraction_import_facture import extraire_brouillon_facture
from app.services.extraction_texte_facture import OcrIndisponibleError
from app.services.generation_facture_pdf import generer_pdf_facture
from app.services.numerotation_facture import (
    SequenceRompueError,
    generer_prochain_numero,
    verifier_numero_sequentiel,
)
from app.services.relations import obtenir_ou_creer_relation
from app.services.roles import ROLES_VALIDATEURS, resoudre_pme_id

_ROLES_GESTION_FACTURES = [RoleUtilisateur.MEMBRE_PME, RoleUtilisateur.ADMIN]

router = APIRouter(
    prefix="/factures",
    tags=["factures"],
)

_UPLOAD_ROOT = Path(__file__).resolve().parents[2] / "uploads" / "factures"
_UPLOADS_MOUNT = Path(__file__).resolve().parents[2] / "uploads"

_COLONNES_IMPORT = [
    "numero_facture",
    "donneur_ordre_id",
    "date_emission",
    "date_echeance",
    "piece_justificative_url",
]

_ROLE_VALIDATEUR_PAR_ROLE_UTILISATEUR: dict[RoleUtilisateur, RoleValidateur] = {
    RoleUtilisateur.VALIDATEUR_1: RoleValidateur.VALIDATEUR_1,
    RoleUtilisateur.VALIDATEUR_2: RoleValidateur.VALIDATEUR_2,
}


def _get_facture_or_404(db: Session, facture_id: uuid.UUID) -> Facture:
    facture = db.get(Facture, facture_id)
    if facture is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Facture introuvable")
    return facture


def _construire_facture_out(db: Session, facture: Facture) -> FactureOut:
    """Attache premiere_validation (nom, role, date) quand la facture attend encore la
    seconde validation, pour affichage direct cote frontend sans requete supplementaire."""
    sortie = FactureOut.model_validate(facture)

    validations = (
        db.query(ValidationFacture)
        .filter(ValidationFacture.facture_id == facture.id)
        .order_by(ValidationFacture.date_validation.asc())
        .all()
    )
    sortie.historique_validations = [
        PremiereValidationInfo(
            nom=v.utilisateur.nom,
            role_validateur=v.role_validateur,
            date_validation=v.date_validation,
        )
        for v in validations
    ]

    if facture.statut == StatutFacture.VALIDATION_COMPLEMENTAIRE_REQUISE and validations:
        sortie.premiere_validation = sortie.historique_validations[0]

    return sortie


def _sauvegarder_pdf(facture_id: uuid.UUID, nom_fichier: str, contenu: bytes) -> str:
    dossier = _UPLOAD_ROOT / str(facture_id)
    dossier.mkdir(parents=True, exist_ok=True)
    chemin = dossier / nom_fichier
    chemin.write_bytes(contenu)
    return f"/uploads/factures/{facture_id}/{nom_fichier}"


def _lire_pdf_local(piece_justificative_url: str) -> bytes | None:
    """Pour l'import batch : piece_justificative_url doit pointer vers un fichier deja
    heberge sous /uploads (meme convention que le televersement direct) - on ne va
    jamais chercher un fichier a une URL externe arbitraire (risque SSRF). Retourne None
    si le chemin ne respecte pas cette convention ou si le fichier est introuvable."""
    if not piece_justificative_url.startswith("/uploads/"):
        return None
    chemin_relatif = piece_justificative_url.removeprefix("/uploads/")
    chemin = (_UPLOADS_MOUNT / chemin_relatif).resolve()
    if _UPLOADS_MOUNT.resolve() not in chemin.parents:
        return None
    if not chemin.is_file():
        return None
    return chemin.read_bytes()


def _appliquer_resultat_conformite(facture: Facture, resultat: ResultatConformite) -> None:
    champs = resultat.champs_extraits
    taux = champs.taux_tva if champs.taux_tva is not None else Decimal("0.18")

    facture.montant_ht = champs.montant_ht if champs.montant_ht is not None else Decimal("0.00")
    facture.taux_tva = taux
    facture.montant_tva = champs.montant_tva if champs.montant_tva is not None else Decimal("0.00")
    facture.montant_ttc = champs.montant_ttc if champs.montant_ttc is not None else Decimal("0.00")
    facture.ninea_emetteur_extrait = champs.ninea_emetteur
    facture.code_validation_dgid = champs.code_validation_dgid
    facture.conformite_verifiee = True

    notes = list(resultat.motifs_rejet) + list(resultat.avertissements)
    facture.motifs_rejet_conformite = notes or None
    facture.statut = StatutFacture.EMISE if resultat.conforme else StatutFacture.REJETEE_CONFORMITE


def _verifier_et_construire_facture(
    db: Session,
    *,
    pme_id: uuid.UUID,
    numero_facture: str,
    donneur_ordre_id: uuid.UUID,
    date_emission: date,
    date_echeance: date,
    piece_justificative_url: str,
    description: str | None,
    devise: str,
    source_creation: SourceCreationFacture,
    contenu_pdf: bytes,
) -> Facture:
    donneur_ordre = db.get(Entreprise, donneur_ordre_id)
    if donneur_ordre is None or donneur_ordre.type != TypeEntreprise.GRANDE_ENTREPRISE:
        raise ValueError("Le donneur d'ordre indique est introuvable ou n'est pas une grande entreprise")

    if date_echeance <= date_emission:
        raise ValueError("La date d'echeance doit etre posterieure a la date d'emission")

    facture = Facture(
        pme_id=pme_id,
        numero_facture=numero_facture,
        donneur_ordre_id=donneur_ordre_id,
        montant_ht=Decimal("0.00"),
        montant_tva=Decimal("0.00"),
        montant_ttc=Decimal("0.00"),
        devise=devise,
        date_emission=date_emission,
        date_echeance=date_echeance,
        duree_jours=(date_echeance - date_emission).days,
        piece_justificative_url=piece_justificative_url,
        description=description,
        source_creation=source_creation,
        statut=StatutFacture.EMISE,
    )

    resultat = verifier_conformite_facture(db, contenu_pdf, pme_id)
    _appliquer_resultat_conformite(facture, resultat)
    return facture


@router.post("", response_model=FactureOut, status_code=status.HTTP_201_CREATED)
async def creer_facture(
    fichier: UploadFile,
    numero_facture: str = Form(...),
    donneur_ordre_id: uuid.UUID = Form(...),
    date_emission: date = Form(...),
    date_echeance: date = Form(...),
    devise: str = Form("FCFA"),
    description: str | None = Form(None),
    pme_id: uuid.UUID | None = Form(None, description="Requis pour un admin ; ignore pour un membre_pme"),
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(require_role(_ROLES_GESTION_FACTURES)),
):
    pme_id = resoudre_pme_id(current_user, pme_id)
    contenu = await fichier.read()
    facture_id = uuid.uuid4()
    url = _sauvegarder_pdf(facture_id, fichier.filename or "facture.pdf", contenu)

    try:
        facture = _verifier_et_construire_facture(
            db,
            pme_id=pme_id,
            numero_facture=numero_facture,
            donneur_ordre_id=donneur_ordre_id,
            date_emission=date_emission,
            date_echeance=date_echeance,
            piece_justificative_url=url,
            description=description,
            devise=devise,
            source_creation=SourceCreationFacture.SAISIE_MANUELLE,
            contenu_pdf=contenu,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    facture.id = facture_id
    db.add(facture)
    db.flush()
    enregistrer_audit(
        db,
        entite_type="Facture",
        entite_id=facture.id,
        action="creation",
        utilisateur_id=current_user.id,
        valeur_apres={
            "numero_facture": facture.numero_facture,
            "montant_ttc": str(facture.montant_ttc),
            "statut": facture.statut.value,
            "conforme": facture.statut != StatutFacture.REJETEE_CONFORMITE,
        },
    )
    db.commit()
    db.refresh(facture)
    return facture


def _recalculer_totaux_lignes(lignes: list[LigneFacture]) -> Decimal:
    """Recalcule montant_ligne = quantite * prix_unitaire sur chaque ligne (jamais saisi
    independamment) et retourne la somme, qui devient montant_ht de la facture."""
    montant_ht = Decimal("0.00")
    for ligne in lignes:
        ligne.montant_ligne = (ligne.quantite * ligne.prix_unitaire).quantize(Decimal("0.01"))
        montant_ht += ligne.montant_ligne
    return montant_ht


@router.post(
    "/native",
    response_model=FactureOut,
    status_code=status.HTTP_201_CREATED,
    summary="Cree une facture brouillon avec lignes d'articles et genere un apercu PDF",
    description=(
        "Contrairement a POST /factures (PDF televerse par la PME, verifie par "
        "app.services.conformite_facture), le document est ici genere par Cedra a partir "
        "des lignes fournies : sa fiabilite n'a donc pas besoin d'etre verifiee apres "
        "coup. La facture nait au statut `brouillon`, sans numero (jamais saisi par "
        "l'utilisateur) : elle reste librement modifiable (PATCH /{id}/lignes) et "
        "supprimable (DELETE /{id}) tant qu'elle n'a pas ete transmise au donneur "
        "d'ordre via POST /{id}/transmettre, seul moment ou l'outil lui attribue son "
        "numero definitif."
    ),
)
def creer_facture_native(
    payload: FactureNativeCreate,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(require_role(_ROLES_GESTION_FACTURES)),
):
    pme_id = resoudre_pme_id(current_user, payload.pme_id)

    donneur_ordre = db.get(Entreprise, payload.donneur_ordre_id)
    if donneur_ordre is None or donneur_ordre.type != TypeEntreprise.GRANDE_ENTREPRISE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Le donneur d'ordre indique est introuvable ou n'est pas une grande entreprise",
        )

    pme = db.get(Entreprise, pme_id)

    lignes_orm = [
        LigneFacture(
            ordre=i,
            designation=l.designation,
            description=l.description,
            quantite=l.quantite,
            prix_unitaire=l.prix_unitaire,
            montant_ligne=Decimal("0.00"),
        )
        for i, l in enumerate(payload.lignes, start=1)
    ]
    montant_ht = _recalculer_totaux_lignes(lignes_orm)
    montant_tva = (montant_ht * payload.taux_tva).quantize(Decimal("0.01"))
    montant_ttc = montant_ht + montant_tva

    facture = Facture(
        pme_id=pme_id,
        numero_facture=None,
        donneur_ordre_id=payload.donneur_ordre_id,
        montant_ht=montant_ht,
        taux_tva=payload.taux_tva,
        montant_tva=montant_tva,
        montant_ttc=montant_ttc,
        devise="FCFA",
        date_emission=payload.date_emission,
        date_echeance=payload.date_echeance,
        duree_jours=(payload.date_echeance - payload.date_emission).days,
        piece_justificative_url="",
        description=payload.notes,
        source_creation=SourceCreationFacture.CREATION_NATIVE,
        statut=StatutFacture.BROUILLON,
        conformite_verifiee=False,
    )
    facture.lignes = lignes_orm
    db.add(facture)
    db.flush()

    obtenir_ou_creer_relation(db, pme_id=pme_id, donneur_ordre_id=payload.donneur_ordre_id)

    pdf_bytes = generer_pdf_facture(facture, pme, donneur_ordre)
    facture.piece_justificative_url = _sauvegarder_pdf(facture.id, "facture.pdf", pdf_bytes)

    enregistrer_audit(
        db,
        entite_type="Facture",
        entite_id=facture.id,
        action="creation_native",
        utilisateur_id=current_user.id,
        valeur_apres={
            "statut": facture.statut.value,
            "montant_ttc": str(facture.montant_ttc),
            "nombre_lignes": len(lignes_orm),
        },
    )
    db.commit()
    db.refresh(facture)
    return _construire_facture_out(db, facture)


@router.patch(
    "/{facture_id}/lignes",
    response_model=FactureOut,
    summary="Remplace les lignes d'une facture a creation native et regenere son PDF",
    description=(
        "Accepte la liste complete des lignes souhaitees (avec `id` pour une ligne "
        "existante a conserver/modifier, sans `id` pour une nouvelle ligne) : toute ligne "
        "existante absente de la liste est supprimee. N'est autorise que tant que la "
        "facture est au statut `brouillon`, avant sa transmission au donneur d'ordre "
        "(POST /{facture_id}/transmettre) : une fois transmise, elle est immuable."
    ),
)
def modifier_lignes_facture(
    facture_id: uuid.UUID,
    payload: FactureLignesUpdateRequest,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(require_role(_ROLES_GESTION_FACTURES)),
):
    facture = _get_facture_or_404(db, facture_id)
    if current_user.role != RoleUtilisateur.ADMIN and facture.pme_id != current_user.entreprise_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cette facture ne vous appartient pas")
    if facture.source_creation != SourceCreationFacture.CREATION_NATIVE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Seules les factures a creation native ont des lignes editables",
        )
    if facture.statut != StatutFacture.BROUILLON:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Les lignes ne sont modifiables que tant que la facture est au statut "
                f"'brouillon' (statut actuel : '{facture.statut.value}')"
            ),
        )

    lignes_existantes = {ligne.id: ligne for ligne in facture.lignes}
    ids_conserves = {l.id for l in payload.lignes if l.id is not None}
    for ligne_id, ligne in lignes_existantes.items():
        if ligne_id not in ids_conserves:
            db.delete(ligne)

    lignes_finales = []
    for i, l in enumerate(payload.lignes, start=1):
        if l.id is not None and l.id in lignes_existantes:
            ligne_orm = lignes_existantes[l.id]
            ligne_orm.ordre = i
            ligne_orm.designation = l.designation
            ligne_orm.description = l.description
            ligne_orm.quantite = l.quantite
            ligne_orm.prix_unitaire = l.prix_unitaire
        else:
            ligne_orm = LigneFacture(
                facture_id=facture.id,
                ordre=i,
                designation=l.designation,
                description=l.description,
                quantite=l.quantite,
                prix_unitaire=l.prix_unitaire,
                montant_ligne=Decimal("0.00"),
            )
            db.add(ligne_orm)
        lignes_finales.append(ligne_orm)

    montant_ht = _recalculer_totaux_lignes(lignes_finales)
    montant_tva = (montant_ht * facture.taux_tva).quantize(Decimal("0.01"))
    montant_ttc = montant_ht + montant_tva

    avant = {"montant_ht": str(facture.montant_ht), "nombre_lignes": len(lignes_existantes)}
    facture.montant_ht = montant_ht
    facture.montant_tva = montant_tva
    facture.montant_ttc = montant_ttc

    db.flush()
    db.expire(facture, ["lignes"])

    pme = db.get(Entreprise, facture.pme_id)
    donneur_ordre = db.get(Entreprise, facture.donneur_ordre_id)
    pdf_bytes = generer_pdf_facture(facture, pme, donneur_ordre)
    facture.piece_justificative_url = _sauvegarder_pdf(facture.id, "facture.pdf", pdf_bytes)

    enregistrer_audit(
        db,
        entite_type="Facture",
        entite_id=facture.id,
        action="modification_lignes",
        utilisateur_id=current_user.id,
        valeur_avant=avant,
        valeur_apres={"montant_ht": str(facture.montant_ht), "nombre_lignes": len(lignes_finales)},
    )
    db.commit()
    db.refresh(facture)
    return _construire_facture_out(db, facture)


@router.post(
    "/{facture_id}/transmettre",
    response_model=FactureOut,
    summary="Transmet une facture brouillon au donneur d'ordre : lui attribue son numero definitif",
    description=(
        "Seul moment ou l'outil attribue le numero de facture (jamais saisi par "
        "l'utilisateur), en continuant sans trou la sequence `FA-{annee}-NNNN` de la "
        "PME. La facture devient `emise` et entre dans le circuit de double validation "
        "du donneur d'ordre ; elle n'est alors plus modifiable ni supprimable."
    ),
)
def transmettre_facture(
    facture_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(require_role(_ROLES_GESTION_FACTURES)),
):
    facture = _get_facture_or_404(db, facture_id)
    if current_user.role != RoleUtilisateur.ADMIN and facture.pme_id != current_user.entreprise_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cette facture ne vous appartient pas")
    if facture.source_creation != SourceCreationFacture.CREATION_NATIVE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Seules les factures a creation native suivent le circuit brouillon -> transmission",
        )
    if facture.statut != StatutFacture.BROUILLON:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Seule une facture au statut 'brouillon' peut etre transmise "
                f"(statut actuel : '{facture.statut.value}')"
            ),
        )

    avant = {"statut": facture.statut.value, "numero_facture": facture.numero_facture}
    facture.numero_facture = generer_prochain_numero(db, facture.pme_id, facture.date_emission.year)

    pme = db.get(Entreprise, facture.pme_id)
    donneur_ordre = db.get(Entreprise, facture.donneur_ordre_id)
    # Un acheteur cree ad-hoc (fiche minimale, statut_fiche pre_inscrite) n'a pas encore
    # d'utilisateurs validateurs ni de KYC : la facture reste bloquee jusqu'a ce qu'il
    # termine son propre onboarding (bascule automatique, voir PATCH /entreprises/{id}/kyc).
    facture.statut = (
        StatutFacture.EN_ATTENTE_KYC_ACHETEUR
        if donneur_ordre.statut_fiche == StatutFiche.PRE_INSCRITE
        else StatutFacture.EMISE
    )
    pdf_bytes = generer_pdf_facture(facture, pme, donneur_ordre)
    facture.piece_justificative_url = _sauvegarder_pdf(facture.id, "facture.pdf", pdf_bytes)

    enregistrer_audit(
        db,
        entite_type="Facture",
        entite_id=facture.id,
        action="transmission",
        utilisateur_id=current_user.id,
        valeur_avant=avant,
        valeur_apres={"statut": facture.statut.value, "numero_facture": facture.numero_facture},
    )
    db.commit()
    db.refresh(facture)
    return _construire_facture_out(db, facture)


@router.delete(
    "/{facture_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Supprime une facture brouillon, jamais transmise au donneur d'ordre",
)
def supprimer_facture(
    facture_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(require_role(_ROLES_GESTION_FACTURES)),
):
    facture = _get_facture_or_404(db, facture_id)
    if current_user.role != RoleUtilisateur.ADMIN and facture.pme_id != current_user.entreprise_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cette facture ne vous appartient pas")
    if facture.statut != StatutFacture.BROUILLON:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Seule une facture au statut 'brouillon' peut etre supprimee "
                f"(statut actuel : '{facture.statut.value}')"
            ),
        )

    enregistrer_audit(
        db,
        entite_type="Facture",
        entite_id=facture.id,
        action="suppression_brouillon",
        utilisateur_id=current_user.id,
        valeur_avant={"montant_ttc": str(facture.montant_ttc), "nombre_lignes": len(facture.lignes)},
        valeur_apres={"statut": "supprimee"},
    )
    shutil.rmtree(_UPLOAD_ROOT / str(facture.id), ignore_errors=True)
    db.delete(facture)
    db.commit()


@router.post(
    "/{facture_id}/resoumettre",
    response_model=FactureOut,
    summary="Resoumet un nouveau PDF pour une facture rejetee pour non-conformite",
    description=(
        "Accessible uniquement si la facture est au statut `rejetee_conformite`. Relance "
        "systematiquement le controle de conformite sur le nouveau document ; la facture "
        "ne repasse au statut `emise` que si le nouveau document est conforme (jamais de "
        "changement de statut sans repasser par le controle)."
    ),
)
async def resoumettre_facture(
    facture_id: uuid.UUID,
    fichier: UploadFile,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(require_role(_ROLES_GESTION_FACTURES)),
):
    facture = _get_facture_or_404(db, facture_id)
    if current_user.role != RoleUtilisateur.ADMIN and facture.pme_id != current_user.entreprise_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cette facture ne vous appartient pas")
    if facture.statut != StatutFacture.REJETEE_CONFORMITE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Seule une facture au statut 'rejetee_conformite' peut etre resoumise (statut actuel : '{facture.statut.value}')",
        )

    contenu = await fichier.read()
    url = _sauvegarder_pdf(facture.id, fichier.filename or "facture.pdf", contenu)

    avant = {"statut": facture.statut.value, "motifs_rejet_conformite": facture.motifs_rejet_conformite}

    resultat = verifier_conformite_facture(db, contenu, facture.pme_id)
    facture.piece_justificative_url = url
    _appliquer_resultat_conformite(facture, resultat)

    enregistrer_audit(
        db,
        entite_type="Facture",
        entite_id=facture.id,
        action="resoumission_conformite",
        utilisateur_id=current_user.id,
        valeur_avant=avant,
        valeur_apres={"statut": facture.statut.value, "motifs_rejet_conformite": facture.motifs_rejet_conformite},
    )
    db.commit()
    db.refresh(facture)
    return facture


@router.post(
    "/extraction-ocr",
    response_model=FactureExtractionOut,
    summary="Extrait un brouillon de facture (dates, TVA, montants, lignes) depuis un PDF ou une photo, pour pre-remplir le formulaire de creation",
)
async def extraire_facture_pour_creation(
    fichier: UploadFile,
    current_user: Utilisateur = Depends(require_role(_ROLES_GESTION_FACTURES)),
):
    contenu = await fichier.read()
    try:
        brouillon = extraire_brouillon_facture(contenu, fichier.content_type)
    except OcrIndisponibleError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc

    return FactureExtractionOut(
        via_ocr=brouillon.via_ocr,
        numero_facture=brouillon.numero_facture,
        date_emission=brouillon.date_emission,
        date_echeance=brouillon.date_echeance,
        taux_tva=brouillon.taux_tva,
        montant_ht=brouillon.montant_ht,
        montant_tva=brouillon.montant_tva,
        montant_ttc=brouillon.montant_ttc,
        lignes=[
            LigneFactureExtraiteOut(designation=l.designation, quantite=l.quantite, prix_unitaire=l.prix_unitaire)
            for l in brouillon.lignes
        ],
        avertissements=brouillon.avertissements,
    )


@router.post("/import", response_model=FactureImportRapport)
async def importer_factures(
    fichier: UploadFile,
    pme_id: uuid.UUID | None = Form(None, description="Requis pour un admin ; ignore pour un membre_pme"),
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(require_role(_ROLES_GESTION_FACTURES)),
):
    pme_id = resoudre_pme_id(current_user, pme_id)
    contenu = await fichier.read()
    nom = (fichier.filename or "").lower()
    try:
        if nom.endswith(".csv"):
            dataframe = pd.read_csv(io.BytesIO(contenu))
        else:
            dataframe = pd.read_excel(io.BytesIO(contenu))
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Fichier illisible : {exc}") from exc

    manquantes = [colonne for colonne in _COLONNES_IMPORT if colonne not in dataframe.columns]
    if manquantes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Colonnes manquantes dans le fichier : {', '.join(manquantes)}",
        )

    details: list[ImportLigneResultat] = []
    for index, ligne in dataframe.iterrows():
        numero_ligne = index + 2  # +1 pour index 0-based, +1 pour l'en-tete
        try:
            verifier_numero_sequentiel(db, pme_id, str(ligne["numero_facture"]))

            piece_url = str(ligne["piece_justificative_url"])
            contenu_pdf = _lire_pdf_local(piece_url)
            if contenu_pdf is None:
                raise ValueError(
                    "piece_justificative_url doit pointer vers un document deja televerse "
                    "sous /uploads/... pour permettre le controle de conformite"
                )

            facture = _verifier_et_construire_facture(
                db,
                pme_id=pme_id,
                numero_facture=str(ligne["numero_facture"]),
                donneur_ordre_id=uuid.UUID(str(ligne["donneur_ordre_id"])),
                date_emission=pd.to_datetime(ligne["date_emission"]).date(),
                date_echeance=pd.to_datetime(ligne["date_echeance"]).date(),
                piece_justificative_url=piece_url,
                description=None if pd.isna(ligne.get("description")) else str(ligne["description"]),
                devise="FCFA",
                source_creation=SourceCreationFacture.IMPORT_FICHIER,
                contenu_pdf=contenu_pdf,
            )
            db.add(facture)
            db.flush()
            details.append(
                ImportLigneResultat(
                    ligne=numero_ligne,
                    succes=True,
                    facture_id=facture.id,
                    conforme=facture.statut != StatutFacture.REJETEE_CONFORMITE,
                    motifs_rejet_conformite=facture.motifs_rejet_conformite,
                )
            )
        except Exception as exc:
            db.rollback()
            details.append(ImportLigneResultat(ligne=numero_ligne, succes=False, erreur=str(exc)))

    db.commit()
    succes = sum(1 for d in details if d.succes)
    return FactureImportRapport(total_lignes=len(details), succes=succes, echecs=len(details) - succes, details=details)


@router.get("", response_model=list[FactureOut])
def lister_factures(
    response: Response,
    pme_id: uuid.UUID | None = None,
    donneur_ordre_id: uuid.UUID | None = None,
    numero: str | None = None,
    statut: StatutFacture | None = None,
    date_debut: date | None = None,
    date_fin: date | None = None,
    entierement_validee: bool | None = None,
    page: int | None = None,
    per_page: int | None = None,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user),
):
    query = db.query(Facture)

    if current_user.role == RoleUtilisateur.MEMBRE_PME:
        # Jamais deduit d'un pme_id fourni par le client pour ce role : toujours sa
        # propre entreprise.
        query = query.filter(Facture.pme_id == current_user.entreprise_id)
    elif current_user.role in ROLES_VALIDATEURS:
        query = query.filter(Facture.donneur_ordre_id == current_user.entreprise_id)
    elif current_user.role == RoleUtilisateur.ADMIN and pme_id is not None:
        query = query.filter(Facture.pme_id == pme_id)

    if donneur_ordre_id is not None:
        query = query.filter(Facture.donneur_ordre_id == donneur_ordre_id)
    if numero is not None:
        query = query.filter(Facture.numero_facture.ilike(f"%{numero}%"))
    if statut is not None:
        query = query.filter(Facture.statut == statut)
    if date_debut is not None:
        query = query.filter(Facture.date_emission >= date_debut)
    if date_fin is not None:
        query = query.filter(Facture.date_emission <= date_fin)
    if entierement_validee:
        sous_requete = (
            db.query(ValidationFacture.facture_id)
            .group_by(ValidationFacture.facture_id)
            .having(func.count(ValidationFacture.id) >= 2)
        )
        query = query.filter(Facture.id.in_(sous_requete))

    query = query.order_by(Facture.created_at.desc())

    # Pagination optionnelle (page/per_page) : n'affecte jamais les appelants existants
    # (dashboards, agregations) qui ne passent pas ces parametres et continuent de
    # recevoir la liste complete. Le total (avant slicing) est expose via l'entete
    # X-Total-Count plutot que de changer la forme de la reponse (compatibilite).
    if page is not None or per_page is not None:
        page = page or 1
        per_page = per_page or 25
        response.headers["X-Total-Count"] = str(query.count())
        query = query.offset((page - 1) * per_page).limit(per_page)

    factures = query.all()
    return [_construire_facture_out(db, facture) for facture in factures]


@router.get("/{facture_id}", response_model=FactureOut)
def obtenir_facture(
    facture_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user),
):
    facture = _get_facture_or_404(db, facture_id)
    return _construire_facture_out(db, facture)


@router.post(
    "/{facture_id}/valider",
    response_model=FactureOut,
    summary="Valide une facture avec le role validateur_1 ou validateur_2 de l'appelant",
    description=(
        "La double validation est **systematique et sans seuil de montant** : toute facture "
        "exige une validation validateur_1 ET une validation validateur_2 de la meme "
        "entreprise donneur d'ordre avant de passer a `validee`, quel que soit son montant. "
        "L'ordre chronologique n'a pas d'importance (validateur_2 peut valider avant "
        "validateur_1) ; ce qui compte est d'avoir recu une validation de chaque role. "
        "Une seule validation par role et par facture : si un validateur_1 a deja valide, "
        "aucun autre validateur_1 (meme un compte different) ne peut valider a nouveau avec "
        "ce role. Statut intermediaire `validation_complementaire_requise` apres la "
        "premiere validation, avec le detail de qui a valide en premier renvoye dans "
        "`premiere_validation`."
    ),
)
def valider_facture(
    facture_id: uuid.UUID,
    payload: FactureValiderRequest,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(require_role(list(ROLES_VALIDATEURS))),
):
    facture = _get_facture_or_404(db, facture_id)

    if facture.donneur_ordre_id != current_user.entreprise_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Vous ne pouvez valider que les factures adressees a votre entreprise",
        )

    if facture.statut not in (StatutFacture.EMISE, StatutFacture.VALIDATION_COMPLEMENTAIRE_REQUISE):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Impossible de valider une facture au statut '{facture.statut.value}'",
        )

    role_validateur = _ROLE_VALIDATEUR_PAR_ROLE_UTILISATEUR[current_user.role]

    validations_existantes = db.query(ValidationFacture).filter(ValidationFacture.facture_id == facture.id).all()
    roles_ayant_valide = {v.role_validateur for v in validations_existantes}
    if role_validateur in roles_ayant_valide:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cette facture a deja recu une validation '{role_validateur.value}'",
        )

    validation = ValidationFacture(
        facture_id=facture.id,
        utilisateur_id=current_user.id,
        role_validateur=role_validateur,
        commentaire=payload.commentaire,
    )
    db.add(validation)

    roles_ayant_valide.add(role_validateur)
    avant = {"statut": facture.statut.value}

    if roles_ayant_valide >= {RoleValidateur.VALIDATEUR_1, RoleValidateur.VALIDATEUR_2}:
        facture.statut = StatutFacture.VALIDEE
    else:
        facture.statut = StatutFacture.VALIDATION_COMPLEMENTAIRE_REQUISE

    enregistrer_audit(
        db,
        entite_type="Facture",
        entite_id=facture.id,
        action="validation",
        utilisateur_id=current_user.id,
        valeur_avant=avant,
        valeur_apres={"statut": facture.statut.value, "role_validateur": role_validateur.value},
    )
    db.commit()
    db.refresh(facture)
    return _construire_facture_out(db, facture)


@router.post("/{facture_id}/rejeter", response_model=FactureOut)
def rejeter_facture(
    facture_id: uuid.UUID,
    payload: FactureRejetRequest,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(require_role(list(ROLES_VALIDATEURS))),
):
    facture = _get_facture_or_404(db, facture_id)

    if facture.donneur_ordre_id != current_user.entreprise_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Vous ne pouvez rejeter que les factures adressees a votre entreprise",
        )

    avant = {"statut": facture.statut.value}
    facture.statut = StatutFacture.REJETEE

    enregistrer_audit(
        db,
        entite_type="Facture",
        entite_id=facture.id,
        action="rejet",
        utilisateur_id=current_user.id,
        valeur_avant=avant,
        valeur_apres={"statut": facture.statut.value, "commentaire": payload.commentaire},
    )
    db.commit()
    db.refresh(facture)
    return facture
