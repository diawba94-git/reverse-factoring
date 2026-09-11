import uuid
from datetime import date as date_type
from datetime import timedelta
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models.cheque_garantie import ChequeGarantie
from app.models.enums import RoleUtilisateur
from app.models.facture import Facture
from app.models.utilisateur import Utilisateur
from app.schemas.cheque_garantie import ChequeGarantieOut
from app.services.audit import enregistrer_audit

router = APIRouter(prefix="/factures/{facture_id}/cheque", tags=["cheques"])

_UPLOAD_ROOT = Path(__file__).resolve().parents[2] / "uploads" / "cheques"

_TOLERANCE_ECHEANCE = timedelta(days=15)


def _get_facture_pme_ou_404(db: Session, facture_id: uuid.UUID, current_user: Utilisateur) -> Facture:
    facture = db.get(Facture, facture_id)
    if facture is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Facture introuvable")
    if current_user.role != RoleUtilisateur.ADMIN and facture.pme_id != current_user.entreprise_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cette facture ne vous appartient pas")
    return facture


@router.post(
    "",
    response_model=ChequeGarantieOut,
    status_code=status.HTTP_201_CREATED,
    summary="Declare un cheque de garantie deja recu pour cette facture (PME/admin)",
    description=(
        "Optionnel, declarable des la creation de la facture — bien avant qu'une Avance "
        "n'existe (doc §5.3bis). Reste en statut `declare` (garantie non fiable) tant que "
        "le donneur d'ordre ne l'a pas confirme lors de sa validation de la facture."
    ),
)
async def declarer_cheque(
    facture_id: uuid.UUID,
    numero_cheque: str,
    banque_emettrice: str,
    date_encaissement_prevue: date_type,
    fichier: UploadFile,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user),
):
    facture = _get_facture_pme_ou_404(db, facture_id, current_user)
    if facture.cheque_garantie is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Un chèque est déjà déclaré pour cette facture")

    ecart = abs((date_encaissement_prevue - facture.date_echeance).days)
    if ecart > _TOLERANCE_ECHEANCE.days:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                "La date d'encaissement prévue doit être cohérente avec l'échéance de la facture "
                f"({facture.date_echeance.isoformat()}, tolérance {_TOLERANCE_ECHEANCE.days} jours)"
            ),
        )

    dossier = _UPLOAD_ROOT / str(facture_id)
    dossier.mkdir(parents=True, exist_ok=True)
    chemin = dossier / fichier.filename
    contenu = await fichier.read()
    chemin.write_bytes(contenu)

    cheque = ChequeGarantie(
        facture_id=facture.id,
        declare_par_utilisateur_id=current_user.id,
        numero_cheque=numero_cheque,
        banque_emettrice=banque_emettrice,
        date_encaissement_prevue=date_encaissement_prevue,
        piece_jointe_url=f"/uploads/cheques/{facture_id}/{fichier.filename}",
    )
    db.add(cheque)
    db.flush()
    enregistrer_audit(
        db,
        entite_type="ChequeGarantie",
        entite_id=cheque.id,
        action="declaration",
        utilisateur_id=current_user.id,
        valeur_apres={"facture_id": str(facture.id), "numero_cheque": numero_cheque, "banque_emettrice": banque_emettrice},
    )
    db.commit()
    db.refresh(cheque)
    return cheque


@router.get("", response_model=ChequeGarantieOut)
def obtenir_cheque(
    facture_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user),
):
    facture = db.get(Facture, facture_id)
    if facture is None or facture.cheque_garantie is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Aucun chèque déclaré pour cette facture")
    return facture.cheque_garantie
