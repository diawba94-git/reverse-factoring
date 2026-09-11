from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.routers import (
    admin,
    auth,
    avances,
    avoirs,
    cheques,
    dashboard,
    entreprises,
    enveloppes,
    factures,
    faq,
    grilles_tarifaires,
    limites_credit,
    litiges,
    messages,
    partenaire_portefeuille,
    pme_notifications,
    public,
    relations,
    remboursements,
    scores,
    simulation,
    support,
    utilisateurs,
    webhooks,
)

app = FastAPI(
    title="InvoiceUp API",
    description="Plateforme d'affacturage pour PME senegalaises : gestion des factures, "
    "validation, avances et remboursements.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Total-Count"],
)

_uploads_dir = Path(__file__).resolve().parents[1] / "uploads"
_uploads_dir.mkdir(exist_ok=True)
app.mount("/uploads", StaticFiles(directory=_uploads_dir), name="uploads")

app.include_router(auth.router)
app.include_router(admin.router)
app.include_router(entreprises.router)
app.include_router(utilisateurs.router)
app.include_router(factures.router)
app.include_router(cheques.router)
app.include_router(simulation.router)
app.include_router(avances.router)
app.include_router(avoirs.router)
app.include_router(remboursements.router)
app.include_router(grilles_tarifaires.router)
app.include_router(scores.router)
app.include_router(limites_credit.router)
app.include_router(litiges.router)
app.include_router(relations.router)
app.include_router(enveloppes.router)
app.include_router(messages.router)
app.include_router(support.router)
app.include_router(dashboard.router)
app.include_router(webhooks.router)
app.include_router(faq.router)
app.include_router(public.router)
app.include_router(partenaire_portefeuille.router)
app.include_router(pme_notifications.router)


@app.get("/health", tags=["health"])
def health():
    return {"status": "ok"}
