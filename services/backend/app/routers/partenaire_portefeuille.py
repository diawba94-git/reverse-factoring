"""Agregations de portefeuille pour le partenaire financier (doc §5.4/§5.5) : exposition
par donneur d'ordre (avec limite de credit), PME financees, et acheteurs partenaires.
Tout est calcule a la volee a partir des Avances reellement financees par l'appelant —
aucune table dediee, ces vues sont purement des lectures agregees."""

import calendar
import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import require_role
from app.models.avance import Avance
from app.models.cheque_garantie import ChequeGarantie
from app.models.convention_domiciliation import ConventionDomiciliation
from app.models.entreprise import Entreprise
from app.models.enums import RoleUtilisateur, StatutAvance, StatutChequeGarantie, StatutRapprochement, StatutRelation, TypeLimite
from app.models.facture import Facture
from app.models.limite_credit import LimiteCredit
from app.models.relation_pme_donneur_ordre import RelationPmeDonneurOrdre
from app.models.remboursement import Remboursement
from app.models.utilisateur import Utilisateur
from app.schemas.admin import RemboursementSuperviseOut
from app.schemas.partenaire_notification import NotificationPartenaireOut, RapportResumeOut, VolumeMoisOut
from app.schemas.partenaire_portefeuille import AcheteurPartenaireOut, DonneurOrdrePortefeuilleOut, PmeFinanceeOut

router = APIRouter(prefix="/partenaire", tags=["partenaire"])
_SEUIL_NON_LU = timedelta(hours=48)
_SLA_DECISION = timedelta(hours=24)

_ROLE_AGENT = [RoleUtilisateur.AGENT_FINANCIER]


def _paginer(items: list, response: Response, page: int | None, per_page: int | None) -> list:
    """Pagination optionnelle appliquee a une liste deja agregee en memoire (le cout de
    l'agregation reste identique, seul le decoupage final est pagine) : n'affecte jamais
    un appelant qui ne passe pas ces parametres."""
    if page is None and per_page is None:
        return items
    page = page or 1
    per_page = per_page or 25
    response.headers["X-Total-Count"] = str(len(items))
    return items[(page - 1) * per_page : page * per_page]


def _avances_du_partenaire(db: Session, partenaire_id: uuid.UUID) -> list[tuple[Avance, Facture]]:
    return (
        db.query(Avance, Facture)
        .join(Facture, Facture.id == Avance.facture_id)
        .filter(Avance.partenaire_financier_id == partenaire_id)
        .all()
    )


@router.get("/portefeuille", response_model=list[DonneurOrdrePortefeuilleOut])
def portefeuille_par_donneur_ordre(
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(require_role(_ROLE_AGENT)),
):
    lignes = _avances_du_partenaire(db, current_user.entreprise_id)

    par_donneur: dict[uuid.UUID, dict] = {}
    for avance, facture in lignes:
        agg = par_donneur.setdefault(facture.donneur_ordre_id, {"encours": Decimal("0"), "retards": 0})
        if avance.statut == StatutAvance.AVANCE_VERSEE:
            agg["encours"] += avance.montant_solde_du
        if avance.statut == StatutAvance.EN_DEFAUT:
            agg["retards"] += 1

    if not par_donneur:
        return []

    donneurs = db.query(Entreprise).filter(Entreprise.id.in_(par_donneur.keys())).all()
    limites = (
        db.query(LimiteCredit)
        .filter(
            LimiteCredit.partenaire_financier_id == current_user.entreprise_id,
            LimiteCredit.entreprise_cible_id.in_(par_donneur.keys()),
            LimiteCredit.type_limite == TypeLimite.ACHETEUR,
        )
        .all()
    )
    limite_par_donneur = {l.entreprise_cible_id: l for l in limites}

    return [
        DonneurOrdrePortefeuilleOut(
            donneur_ordre_id=d.id,
            raison_sociale=d.raison_sociale,
            encours=par_donneur[d.id]["encours"],
            limite_plafond=limite_par_donneur[d.id].montant_plafond if d.id in limite_par_donneur else None,
            limite_utilisee=limite_par_donneur[d.id].montant_utilise if d.id in limite_par_donneur else None,
            retards=par_donneur[d.id]["retards"],
        )
        for d in donneurs
    ]


@router.get("/remboursements", response_model=list[RemboursementSuperviseOut])
def remboursements_du_partenaire(
    response: Response,
    page: int | None = None,
    per_page: int | None = None,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(require_role(_ROLE_AGENT)),
):
    remboursements = (
        db.query(Remboursement)
        .join(Avance, Avance.id == Remboursement.avance_id)
        .filter(Avance.partenaire_financier_id == current_user.entreprise_id)
        .order_by(Remboursement.created_at.desc())
        .all()
    )
    resultat = [
        RemboursementSuperviseOut(
            id=r.id,
            avance_id=r.avance_id,
            montant_recu=r.montant_recu,
            date_reception=r.date_reception,
            source_entreprise=r.source_entreprise.raison_sociale,
            montant_attendu=r.avance.montant_solde_du,
            ecart=r.montant_recu - r.avance.montant_solde_du,
            statut_rapprochement=r.statut_rapprochement.value,
        )
        for r in remboursements
    ]
    return _paginer(resultat, response, page, per_page)


@router.get("/pme-financees", response_model=list[PmeFinanceeOut])
def pme_financees(
    response: Response,
    page: int | None = None,
    per_page: int | None = None,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(require_role(_ROLE_AGENT)),
):
    lignes = _avances_du_partenaire(db, current_user.entreprise_id)

    par_pme: dict[uuid.UUID, dict] = {}
    for avance, facture in lignes:
        agg = par_pme.setdefault(facture.pme_id, {"encours": Decimal("0"), "factures": set()})
        if avance.statut == StatutAvance.AVANCE_VERSEE:
            agg["encours"] += avance.montant_solde_du
        agg["factures"].add(facture.id)

    if not par_pme:
        return []

    pmes = db.query(Entreprise).filter(Entreprise.id.in_(par_pme.keys())).all()
    resultat = [
        PmeFinanceeOut(
            pme_id=p.id,
            raison_sociale=p.raison_sociale,
            ninea=p.ninea,
            encours=par_pme[p.id]["encours"],
            nombre_factures=len(par_pme[p.id]["factures"]),
        )
        for p in pmes
    ]
    return _paginer(resultat, response, page, per_page)


@router.get("/acheteurs", response_model=list[AcheteurPartenaireOut])
def acheteurs_partenaires(
    response: Response,
    page: int | None = None,
    per_page: int | None = None,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(require_role(_ROLE_AGENT)),
):
    lignes = _avances_du_partenaire(db, current_user.entreprise_id)

    par_donneur: dict[uuid.UUID, dict] = {}
    for avance, facture in lignes:
        agg = par_donneur.setdefault(facture.donneur_ordre_id, {"encours": Decimal("0"), "total": 0, "defauts": 0})
        if avance.statut == StatutAvance.AVANCE_VERSEE:
            agg["encours"] += avance.montant_solde_du
        agg["total"] += 1
        if avance.statut == StatutAvance.EN_DEFAUT:
            agg["defauts"] += 1

    if not par_donneur:
        return []

    donneurs = db.query(Entreprise).filter(Entreprise.id.in_(par_donneur.keys())).all()
    resultat = [
        AcheteurPartenaireOut(
            donneur_ordre_id=d.id,
            raison_sociale=d.raison_sociale,
            secteur_activite=d.secteur_activite,
            encours=par_donneur[d.id]["encours"],
            taux_retard=(
                (Decimal(par_donneur[d.id]["defauts"]) / Decimal(par_donneur[d.id]["total"]) * 100)
                if par_donneur[d.id]["total"]
                else Decimal("0")
            ).quantize(Decimal("0.1")),
        )
        for d in donneurs
    ]
    return _paginer(resultat, response, page, per_page)


def _naive_utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _aware(dt: datetime) -> datetime:
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=timezone.utc)


@router.get(
    "/notifications",
    response_model=list[NotificationPartenaireOut],
    summary="Notifications du partenaire, synthetisees a partir des evenements reels de son portefeuille",
    description=(
        "Aucune table Notification dediee : chaque entree reflete un etat reel (avance en "
        "attente, cheque confirme, remboursement rapproche/en ecart, convention signee) au "
        "moment de l'appel. 'lu' est un heuristique base sur l'anciennete (>48h = lu), il "
        "n'y a pas d'accuse de lecture persiste pour ce MVP."
    ),
)
def notifications_du_partenaire(
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(require_role(_ROLE_AGENT)),
):
    maintenant = _naive_utc_now()
    partenaire_id = current_user.entreprise_id
    notifications: list[NotificationPartenaireOut] = []

    lignes = _avances_du_partenaire(db, partenaire_id)
    facture_par_id = {f.id: f for _, f in lignes}
    pme_ids = {f.pme_id for _, f in lignes} | {f.donneur_ordre_id for _, f in lignes}
    entreprises = {e.id: e for e in db.query(Entreprise).filter(Entreprise.id.in_(pme_ids)).all()} if pme_ids else {}

    for avance, facture in lignes:
        if avance.statut != StatutAvance.EN_ATTENTE_VALIDATION:
            continue
        cree_le = _aware(avance.created_at)
        pme_nom = entreprises[facture.pme_id].raison_sociale if facture.pme_id in entreprises else "—"
        reste = _SLA_DECISION - (maintenant - cree_le)
        if reste < timedelta(hours=4):
            notifications.append(
                NotificationPartenaireOut(
                    type="echeance",
                    titre=f"Décision arrivant à échéance — {facture.numero_facture or 'facture'}, {pme_nom}",
                    description=f"Il vous reste moins de {max(reste, timedelta(0)).seconds // 3600}h pour statuer sur cette demande",
                    date=cree_le,
                    lu=(maintenant - cree_le) > _SEUIL_NON_LU,
                )
            )
        else:
            notifications.append(
                NotificationPartenaireOut(
                    type="opportunite",
                    titre=f"Nouvelle opportunité — {facture.numero_facture or 'facture'}, {pme_nom}",
                    description=f"{facture.montant_ttc:,.0f} FCFA à décider — SLA 24h en cours".replace(",", " "),
                    date=cree_le,
                    lu=(maintenant - cree_le) > _SEUIL_NON_LU,
                )
            )

    cheques = (
        db.query(ChequeGarantie)
        .join(Facture, Facture.id == ChequeGarantie.facture_id)
        .filter(
            Facture.id.in_(facture_par_id.keys()),
            ChequeGarantie.statut.in_(
                [StatutChequeGarantie.CONFIRME_PAR_DONNEUR_ORDRE, StatutChequeGarantie.REMIS_AU_PARTENAIRE, StatutChequeGarantie.ENCAISSE]
            ),
        )
        .all()
    )
    for cheque in cheques:
        facture = facture_par_id.get(cheque.facture_id)
        date_evt = _aware(cheque.date_creation)
        notifications.append(
            NotificationPartenaireOut(
                type="cheque",
                titre=f"Chèque confirmé — {facture.numero_facture if facture else '—'}",
                description=f"Chèque n°{cheque.numero_cheque} confirmé, garantie désormais fiable",
                date=date_evt,
                lu=(maintenant - date_evt) > _SEUIL_NON_LU,
            )
        )

    avance_ids = [a.id for a, _ in lignes]
    remboursements = (
        db.query(Remboursement).filter(Remboursement.avance_id.in_(avance_ids)).all() if avance_ids else []
    )
    for r in remboursements:
        avance = next((a for a, _ in lignes if a.id == r.avance_id), None)
        facture = facture_par_id.get(avance.facture_id) if avance else None
        date_evt = _aware(datetime.combine(r.date_reception, datetime.min.time()))
        if r.statut_rapprochement == StatutRapprochement.ECART_DETECTE:
            ecart = abs(r.montant_recu - avance.montant_solde_du) if avance else Decimal("0")
            notifications.append(
                NotificationPartenaireOut(
                    type="litige",
                    titre=f"Écart de remboursement détecté — {facture.numero_facture if facture else '—'}",
                    description=f"{ecart:,.0f} FCFA d'écart entre le montant attendu et le montant reçu".replace(",", " "),
                    date=date_evt,
                    lu=(maintenant - date_evt) > _SEUIL_NON_LU,
                )
            )
        elif r.statut_rapprochement == StatutRapprochement.RAPPROCHE:
            notifications.append(
                NotificationPartenaireOut(
                    type="remboursement",
                    titre=f"Remboursement rapproché — {facture.numero_facture if facture else '—'}",
                    description=f"{r.montant_recu:,.0f} FCFA reçus et rapprochés".replace(",", " "),
                    date=date_evt,
                    lu=(maintenant - date_evt) > _SEUIL_NON_LU,
                )
            )

    paires = {(f.pme_id, f.donneur_ordre_id) for _, f in lignes}
    if paires:
        relations = (
            db.query(RelationPmeDonneurOrdre)
            .filter(RelationPmeDonneurOrdre.statut == StatutRelation.CONVENTION_SIGNEE)
            .all()
        )
        for relation in relations:
            if (relation.pme_id, relation.donneur_ordre_id) not in paires:
                continue
            date_evt = _aware(relation.date_debut_relation)
            notifications.append(
                NotificationPartenaireOut(
                    type="convention",
                    titre=f"Convention signée — {relation.pme.raison_sociale} ↔ {relation.donneur_ordre.raison_sociale}",
                    description="Les 3 signatures ont été obtenues, compte dédié actif",
                    date=date_evt,
                    lu=(maintenant - date_evt) > _SEUIL_NON_LU,
                )
            )

    notifications.sort(key=lambda n: n.date, reverse=True)
    return notifications


_NOMS_MOIS = ["Jan", "Fév", "Mar", "Avr", "Mai", "Juin", "Juil", "Août", "Sept", "Oct", "Nov", "Déc"]


def _debut_mois(d: date, decalage: int) -> date:
    """decalage=0 -> premier jour du mois de d ; decalage=-1 -> mois precedent, etc."""
    mois_absolu = d.year * 12 + (d.month - 1) + decalage
    annee, mois = divmod(mois_absolu, 12)
    return date(annee, mois + 1, 1)


def _fin_mois(d: date) -> date:
    return date(d.year, d.month, calendar.monthrange(d.year, d.month)[1])


@router.get(
    "/rapports/resume",
    response_model=RapportResumeOut,
    summary="Volume finance sur 6 mois et indicateurs cles du mois en cours, pour le portefeuille de l'appelant",
)
def rapport_resume(
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(require_role(_ROLE_AGENT)),
):
    aujourdhui = date.today()
    lignes = _avances_du_partenaire(db, current_user.entreprise_id)

    volume_par_mois: list[VolumeMoisOut] = []
    for decalage in range(-5, 1):
        debut = _debut_mois(aujourdhui, decalage)
        fin = _fin_mois(debut)
        montant = sum(
            (a.montant_avance_initial for a, _ in lignes if debut <= a.created_at.date() <= fin),
            Decimal("0"),
        )
        volume_par_mois.append(VolumeMoisOut(mois=_NOMS_MOIS[debut.month - 1], montant=montant))

    debut_ce_mois = _debut_mois(aujourdhui, 0)
    debut_mois_dernier = _debut_mois(aujourdhui, -1)
    fin_mois_dernier = _fin_mois(debut_mois_dernier)

    def _montant_finance(debut_periode: date, fin_periode: date) -> Decimal:
        return sum(
            (a.montant_avance_initial for a, _ in lignes if debut_periode <= a.created_at.date() <= fin_periode),
            Decimal("0"),
        )

    def _frais_generes(debut_periode: date, fin_periode: date) -> Decimal:
        return sum(
            (a.part_partenaire for a, _ in lignes if debut_periode <= a.created_at.date() <= fin_periode),
            Decimal("0"),
        )

    def _variation_pct(actuel: Decimal, precedent: Decimal) -> Decimal | None:
        if precedent == 0:
            return None
        return ((actuel - precedent) / precedent * 100).quantize(Decimal("0.1"))

    montant_ce_mois = _montant_finance(debut_ce_mois, aujourdhui)
    montant_mois_dernier = _montant_finance(debut_mois_dernier, fin_mois_dernier)
    frais_ce_mois = _frais_generes(debut_ce_mois, aujourdhui)
    frais_mois_dernier = _frais_generes(debut_mois_dernier, fin_mois_dernier)

    avances_actives = [a for a, _ in lignes if a.statut in (StatutAvance.AVANCE_VERSEE, StatutAvance.SOLDEE)]
    rendement = (
        (sum((a.taeg_annualise for a in avances_actives), Decimal("0")) / len(avances_actives) * 100).quantize(Decimal("0.01"))
        if avances_actives
        else Decimal("0")
    )

    return RapportResumeOut(
        volume_par_mois=volume_par_mois,
        montant_finance_ce_mois=montant_ce_mois,
        variation_montant_finance_pct=_variation_pct(montant_ce_mois, montant_mois_dernier),
        frais_generes_ce_mois=frais_ce_mois,
        variation_frais_generes_pct=_variation_pct(frais_ce_mois, frais_mois_dernier),
        rendement_portefeuille_pct=rendement,
    )


@router.get(
    "/rapports/telecharger",
    summary="Genere un PDF de synthese reel (mensuel, trimestriel ou semestriel) pour le portefeuille de l'appelant",
)
def telecharger_rapport(
    periode: str = "mensuel",
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(require_role(_ROLE_AGENT)),
):
    from fpdf import FPDF

    from app.services.logo_pdf import dessiner_wordmark

    aujourdhui = date.today()
    mois_a_couvrir = {"mensuel": 1, "trimestriel": 3, "semestriel": 6}.get(periode, 1)
    debut_periode = _debut_mois(aujourdhui, -(mois_a_couvrir - 1))

    lignes = _avances_du_partenaire(db, current_user.entreprise_id)
    lignes_periode = [(a, f) for a, f in lignes if a.created_at.date() >= debut_periode]

    montant_finance = sum((a.montant_avance_initial for a, _ in lignes_periode), Decimal("0"))
    frais_generes = sum((a.part_partenaire for a, _ in lignes_periode), Decimal("0"))
    nombre_avances = len(lignes_periode)
    avances_actives = [a for a, _ in lignes_periode if a.statut in (StatutAvance.AVANCE_VERSEE, StatutAvance.SOLDEE)]
    taeg_moyen = (
        (sum((a.taeg_annualise for a in avances_actives), Decimal("0")) / len(avances_actives) * 100)
        if avances_actives
        else Decimal("0")
    )
    defauts = len([a for a, _ in lignes_periode if a.statut == StatutAvance.EN_DEFAUT])
    grille_types = {a.grille_tarifaire.type_partenaire.value for a, _ in lignes_periode if a.grille_tarifaire}
    plafond_legal = Decimal("24") if grille_types == {"imf"} else Decimal("14")

    entreprise = db.get(Entreprise, current_user.entreprise_id)

    pdf = FPDF()
    pdf.add_page()
    dessiner_wordmark(pdf, 15, 12, 9)
    pdf.set_y(28)
    pdf.set_font("Helvetica", "B", 16)
    libelle_periode = {"mensuel": "Rapport mensuel", "trimestriel": "Rapport trimestriel", "semestriel": "Rapport semestriel"}[
        periode if periode in ("mensuel", "trimestriel", "semestriel") else "mensuel"
    ]
    pdf.cell(0, 10, text=libelle_periode, new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", size=10)
    pdf.cell(0, 7, text=f"{entreprise.raison_sociale if entreprise else ''}", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(
        0, 7,
        text=f"Période : {debut_periode.strftime('%d/%m/%Y')} au {aujourdhui.strftime('%d/%m/%Y')}",
        new_x="LMARGIN", new_y="NEXT",
    )
    pdf.ln(6)

    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, text="Synthèse du portefeuille", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", size=10)
    pdf.cell(0, 7, text=f"Nombre d'avances sur la période : {nombre_avances}", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 7, text=f"Montant financé : {montant_finance:,.0f} FCFA".replace(",", " "), new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 7, text=f"Frais générés (votre part) : {frais_generes:,.0f} FCFA".replace(",", " "), new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 7, text=f"TAEG moyen : {taeg_moyen:.2f} %", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)

    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, text="Conformité réglementaire", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", size=10)
    conforme = "Oui" if taeg_moyen <= plafond_legal else "À vérifier"
    pdf.cell(0, 7, text=f"TAEG moyen sous le plafond légal ({plafond_legal:.0f}%) : {conforme}", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 7, text=f"Avances en défaut sur la période : {defauts}", new_x="LMARGIN", new_y="NEXT")

    contenu = bytes(pdf.output())
    nom_fichier = f"rapport-{periode}-{aujourdhui.isoformat()}.pdf"
    return Response(
        content=contenu,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{nom_fichier}"'},
    )
