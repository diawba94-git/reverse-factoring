import uuid
from datetime import date, datetime

from pydantic import BaseModel

from app.models.enums import StatutChequeGarantie


class ChequeGarantieDeclareRequest(BaseModel):
    numero_cheque: str
    banque_emettrice: str
    date_encaissement_prevue: date
    piece_jointe_url: str


class ChequeGarantieOut(BaseModel):
    id: uuid.UUID
    facture_id: uuid.UUID
    numero_cheque: str
    banque_emettrice: str
    date_encaissement_prevue: date
    piece_jointe_url: str
    statut: StatutChequeGarantie
    date_remise_partenaire: datetime | None
    date_creation: datetime

    model_config = {"from_attributes": True}
