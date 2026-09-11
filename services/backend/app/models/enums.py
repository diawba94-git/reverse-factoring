import enum


class TypeEntreprise(str, enum.Enum):
    PME = "PME"
    GRANDE_ENTREPRISE = "GRANDE_ENTREPRISE"
    PARTENAIRE_FINANCIER = "PARTENAIRE_FINANCIER"


class StatutKyc(str, enum.Enum):
    EN_ATTENTE = "en_attente"
    VALIDE = "valide"
    REJETE = "rejete"


class FormeJuridique(str, enum.Enum):
    PERSONNE_PHYSIQUE_ENTREPRISE_INDIVIDUELLE = "personne_physique_entreprise_individuelle"
    GIE = "gie"
    SARL = "sarl"
    SA = "sa"
    AUTRE = "autre"


class RoleUtilisateur(str, enum.Enum):
    ADMIN = "admin"
    MEMBRE_PME = "membre_pme"
    VALIDATEUR_1 = "validateur_1"
    VALIDATEUR_2 = "validateur_2"
    AGENT_FINANCIER = "agent_financier"


class RoleValidateur(str, enum.Enum):
    """Subset of RoleUtilisateur that may appear on a ValidationFacture row. A dedicated
    Postgres enum (rather than reusing role_utilisateur) so the DB itself guarantees a
    validation can never be recorded under a non-validator role."""

    VALIDATEUR_1 = "validateur_1"
    VALIDATEUR_2 = "validateur_2"


class StatutFacture(str, enum.Enum):
    BROUILLON = "brouillon"
    EN_ATTENTE_KYC_ACHETEUR = "en_attente_kyc_acheteur"
    EMISE = "emise"
    VALIDEE = "validee"
    VALIDATION_COMPLEMENTAIRE_REQUISE = "validation_complementaire_requise"
    AVANCE_DEMANDEE = "avance_demandee"
    AVANCE_VERSEE = "avance_versee"
    SOLDEE = "soldee"
    EN_RETARD = "en_retard"
    LITIGE = "litige"
    REJETEE = "rejetee"
    REJETEE_CONFORMITE = "rejetee_conformite"


class SourceCreationFacture(str, enum.Enum):
    SAISIE_MANUELLE = "saisie_manuelle"
    IMPORT_FICHIER = "import_fichier"
    CREATION_NATIVE = "creation_native"


class StatutAvance(str, enum.Enum):
    EN_ATTENTE_VALIDATION = "en_attente_validation"
    AVANCE_VERSEE = "avance_versee"
    SOLDEE = "soldee"
    EN_DEFAUT = "en_defaut"
    REJETEE = "rejetee"


class MethodeVersement(str, enum.Enum):
    WAVE = "wave"
    VIREMENT_BANCAIRE = "virement_bancaire"


class StatutRapprochement(str, enum.Enum):
    EN_ATTENTE = "en_attente"
    RAPPROCHE = "rapproche"
    ECART_DETECTE = "ecart_detecte"


class TypeLimite(str, enum.Enum):
    ACHETEUR = "acheteur"
    FOURNISSEUR = "fournisseur"


class StatutTicket(str, enum.Enum):
    OUVERT = "ouvert"
    EN_COURS = "en_cours"
    RESOLU = "resolu"
    FERME = "ferme"


class StatutFiche(str, enum.Enum):
    """Cycle de vie d'une fiche Entreprise de type GRANDE_ENTREPRISE cree ad-hoc par une PME
    qui lui adresse une premiere facture avant qu'elle n'existe sur la plateforme (voir
    architecture-mvp-affacturage-inverse.md §3.0quater). Une PME/un partenaire s'inscrit
    toujours directement en ACTIVE ; seul un acheteur peut transiter par PRE_INSCRITE."""

    PRE_INSCRITE = "pre_inscrite"
    ACTIVE = "active"


class CauseLitige(str, enum.Enum):
    CHEQUE_SANS_PROVISION = "cheque_sans_provision"
    CONTESTATION_ACHETEUR = "contestation_acheteur"
    ECART_REMBOURSEMENT = "ecart_remboursement"
    AUTRE = "autre"


class StatutLitige(str, enum.Enum):
    OUVERT = "ouvert"
    EN_COURS = "en_cours"
    RESOLU = "resolu"


class StatutRelation(str, enum.Enum):
    PILOTE = "pilote"
    CONVENTION_SIGNEE = "convention_signee"


class StatutCompteDedie(str, enum.Enum):
    EN_OUVERTURE = "en_ouverture"
    ACTIF = "actif"
    CLOTURE = "cloture"


class TypePartenaire(str, enum.Enum):
    BANQUE = "banque"
    IMF = "imf"


class StatutChequeGarantie(str, enum.Enum):
    DECLARE = "declare"
    CONFIRME_PAR_DONNEUR_ORDRE = "confirme_par_donneur_ordre"
    REMIS_AU_PARTENAIRE = "remis_au_partenaire"
    ENCAISSE = "encaisse"
    REJETE_SANS_PROVISION = "rejete_sans_provision"


class ActionLitige(str, enum.Enum):
    CONTACTER_PARTIES = "contacter_parties"
    ENGAGER_RECOUVREMENT = "engager_recouvrement"
    PROPOSER_RESOLUTION = "proposer_resolution"
    MARQUER_RESOLU = "marquer_resolu"


class MotifAvoir(str, enum.Enum):
    RETOUR_PARTIEL = "retour_partiel"
    ERREUR_PRIX = "erreur_prix"
    REMISE_COMMERCIALE = "remise_commerciale"
    AUTRE = "autre"


class StatutAvoir(str, enum.Enum):
    EMIS = "emis"
    CONFIRME_PAR_ACHETEUR = "confirme_par_acheteur"
    REJETE = "rejete"


class StatutCreance(str, enum.Enum):
    EN_ATTENTE = "en_attente"
    PARTIELLEMENT_RECOUVREE = "partiellement_recouvree"
    SOLDEE = "soldee"
