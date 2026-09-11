import logging

from fastapi import APIRouter, Header, Request, status

router = APIRouter(prefix="/webhooks", tags=["webhooks"])

logger = logging.getLogger("webhooks.wave")


@router.post("/wave", status_code=status.HTTP_200_OK)
async def wave_webhook(request: Request, wave_signature: str | None = Header(default=None)):
    """Stub pour les evenements webhook Wave.

    La verification de signature et le traitement des evenements (versement confirme,
    echec de paiement, etc.) seront branches en phase suivante, lorsque l'integration
    Wave reelle sera disponible. Pour l'instant on se contente d'accuser reception.
    """
    corps = await request.body()
    logger.info("Evenement webhook Wave recu (signature=%s, taille=%d octets)", wave_signature, len(corps))
    return {"recu": True}
