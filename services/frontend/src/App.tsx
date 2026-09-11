import { Navigate, Route, Routes } from "react-router-dom";
import { IconSprite } from "./components/shell/IconSprite";
import { Landing } from "./pages/Landing";
import { Login } from "./pages/auth/Login";
import { Register } from "./pages/auth/Register";
import { PendingValidation } from "./pages/auth/PendingValidation";
import { AcheteurRejoindre } from "./pages/acheteur/AcheteurRejoindre";
import { AcheteurSection } from "./pages/acheteur/AcheteurSection";
import { AcheteurOnboarding } from "./pages/acheteur/AcheteurOnboarding";
import { AcheteurDashboard } from "./pages/acheteur/AcheteurDashboard";
import { ComingSoonAcheteurScreen } from "./pages/acheteur/ComingSoonAcheteurScreen";
import { AcheteurFacturesRecues } from "./pages/acheteur/AcheteurFacturesRecues";
import { AcheteurHistorique } from "./pages/acheteur/AcheteurHistorique";
import { AcheteurValidateurs } from "./pages/acheteur/AcheteurValidateurs";
import { AcheteurPaiements } from "./pages/acheteur/AcheteurPaiements";
import { AcheteurAvoirs } from "./pages/acheteur/AcheteurAvoirs";
import { AcheteurParametres } from "./pages/acheteur/AcheteurParametres";
import { PartenaireSection } from "./pages/partenaire/PartenaireSection";
import { PartenaireDashboard } from "./pages/partenaire/PartenaireDashboard";
import { PartenaireDecision } from "./pages/partenaire/PartenaireDecision";
import { PartenaireFinancements } from "./pages/partenaire/PartenaireFinancements";
import { PartenairePortefeuille } from "./pages/partenaire/PartenairePortefeuille";
import { PartenaireRemboursements } from "./pages/partenaire/PartenaireRemboursements";
import { PartenaireConventions } from "./pages/partenaire/PartenaireConventions";
import { PartenairePmePartenaires } from "./pages/partenaire/PartenairePmePartenaires";
import { PartenaireAcheteursPartenaires } from "./pages/partenaire/PartenaireAcheteursPartenaires";
import { PartenaireGrilles } from "./pages/partenaire/PartenaireGrilles";
import { PartenaireRapports } from "./pages/partenaire/PartenaireRapports";
import { PartenaireNotifications } from "./pages/partenaire/PartenaireNotifications";
import { PartenaireAvoirs } from "./pages/partenaire/PartenaireAvoirs";
import { PmeSection } from "./pages/pme/PmeSection";
import { PmeDashboard } from "./pages/pme/PmeDashboard";
import { PmeCreerFacture } from "./pages/pme/PmeCreerFacture";
import { PmeParametres } from "./pages/pme/PmeParametres";
import { PmeNotifications } from "./pages/pme/PmeNotifications";
import { MesFactures } from "./pages/pme/MesFactures";
import { PmeAvoirs } from "./pages/pme/PmeAvoirs";
import { SimulationAvance } from "./pages/pme/SimulationAvance";
import { SuiviDemande } from "./pages/pme/SuiviDemande";
import { GestionUtilisateursPme } from "./pages/pme/GestionUtilisateursPme";
import { AdminSection } from "./pages/admin/AdminSection";
import { AdminDashboard } from "./pages/admin/AdminDashboard";
import { AdminDoublons } from "./pages/admin/AdminDoublons";
import { AdminLitiges } from "./pages/admin/AdminLitiges";
import { AdminUtilisateurs } from "./pages/admin/AdminUtilisateurs";
import { AdminFactures } from "./pages/admin/AdminFactures";
import { AdminAvances } from "./pages/admin/AdminAvances";
import { AdminRemboursements } from "./pages/admin/AdminRemboursements";
import { AdminConventions } from "./pages/admin/AdminConventions";
import { AdminAvoirs } from "./pages/admin/AdminAvoirs";
import { LegacyAdminScreen, ComingSoonAdminScreen } from "./pages/admin/LegacyAdminScreen";
import { AdminGrilles } from "./pages/admin/AdminGrilles";
import { Pilotage } from "./pages/admin/Pilotage";
import { ValidationInscriptions } from "./pages/admin/ValidationInscriptions";
import { EquipeCedra } from "./pages/admin/EquipeCedra";
import { LogsTechniques } from "./pages/admin/LogsTechniques";
import { EntreprisesKyc } from "./pages/admin/EntreprisesKyc";
import { RapportsConsolides } from "./pages/admin/RapportsConsolides";
import { Faq } from "./pages/admin/Faq";
import { Parametres } from "./pages/admin/Parametres";

export function App() {
  return (
    <>
    <IconSprite />
    <Routes>
      <Route path="/" element={<Landing />} />
      <Route path="/login" element={<Login />} />
      <Route path="/register" element={<Register />} />
      <Route path="/pending-validation" element={<PendingValidation />} />

      <Route path="/app/pme" element={<PmeSection />}>
        <Route index element={<PmeDashboard />} />
        <Route path="factures" element={<MesFactures />} />
        <Route path="creer" element={<PmeCreerFacture />} />
        <Route path="avance" element={<SimulationAvance />} />
        <Route path="suivi" element={<SuiviDemande />} />
        <Route path="utilisateurs" element={<GestionUtilisateursPme />} />
        <Route path="notifications" element={<PmeNotifications />} />
        <Route path="avoirs" element={<PmeAvoirs />} />
        <Route path="parametres" element={<PmeParametres />} />
      </Route>
      <Route path="/rejoindre/:token" element={<AcheteurRejoindre />} />
      <Route path="/app/acheteur/onboarding" element={<AcheteurOnboarding />} />
      <Route path="/app/acheteur" element={<AcheteurSection />}>
        <Route index element={<AcheteurDashboard />} />
        <Route path="factures" element={<AcheteurFacturesRecues />} />
        <Route path="historique" element={<AcheteurHistorique />} />
        <Route path="validateurs" element={<AcheteurValidateurs />} />
        <Route path="paiements" element={<AcheteurPaiements />} />
        <Route path="notifications" element={<ComingSoonAcheteurScreen title="Notifications" />} />
        <Route path="avoirs" element={<AcheteurAvoirs />} />
        <Route path="parametres" element={<AcheteurParametres />} />
      </Route>
      <Route path="/app/partenaire" element={<PartenaireSection />}>
        <Route index element={<PartenaireDashboard />} />
        <Route path="opportunites" element={<PartenaireDashboard />} />
        <Route path="decision/:avanceId" element={<PartenaireDecision />} />
        <Route path="financements" element={<PartenaireFinancements />} />
        <Route path="portefeuille" element={<PartenairePortefeuille />} />
        <Route path="remboursements" element={<PartenaireRemboursements />} />
        <Route path="conventions" element={<PartenaireConventions />} />
        <Route path="pme" element={<PartenairePmePartenaires />} />
        <Route path="acheteurs" element={<PartenaireAcheteursPartenaires />} />
        <Route path="rapports" element={<PartenaireRapports />} />
        <Route path="notifications" element={<PartenaireNotifications />} />
        <Route path="grilles" element={<PartenaireGrilles />} />
        <Route path="avoirs" element={<PartenaireAvoirs />} />
      </Route>
      <Route path="/app/admin" element={<AdminSection />}>
        <Route index element={<AdminDashboard />} />
        <Route path="doublons" element={<AdminDoublons />} />
        <Route path="litiges" element={<AdminLitiges />} />
        <Route path="factures" element={<AdminFactures />} />
        <Route path="avances" element={<AdminAvances />} />
        <Route path="remboursements" element={<AdminRemboursements />} />
        <Route path="conventions" element={<AdminConventions />} />
        <Route path="notifications" element={<ComingSoonAdminScreen title="Notifications" />} />
        <Route
          path="rapports"
          element={
            <LegacyAdminScreen title="Rapports">
              <RapportsConsolides />
            </LegacyAdminScreen>
          }
        />
        <Route path="utilisateurs" element={<AdminUtilisateurs />} />
        <Route path="grilles" element={<AdminGrilles />} />
        <Route path="avoirs" element={<AdminAvoirs />} />

        {/* Écrans existants sans emplacement dans la sidebar de la maquette : accès direct par URL. */}
        <Route
          path="pilotage-legacy"
          element={
            <LegacyAdminScreen title="Pilotage">
              <Pilotage />
            </LegacyAdminScreen>
          }
        />
        <Route
          path="inscriptions-legacy"
          element={
            <LegacyAdminScreen title="Validation des inscriptions">
              <ValidationInscriptions />
            </LegacyAdminScreen>
          }
        />
        <Route
          path="kyc-legacy"
          element={
            <LegacyAdminScreen title="Entreprises et KYC">
              <EntreprisesKyc />
            </LegacyAdminScreen>
          }
        />
        <Route
          path="equipe-legacy"
          element={
            <LegacyAdminScreen title="Équipe Cedra">
              <EquipeCedra />
            </LegacyAdminScreen>
          }
        />
        <Route
          path="logs-legacy"
          element={
            <LegacyAdminScreen title="Logs techniques">
              <LogsTechniques />
            </LegacyAdminScreen>
          }
        />
        <Route
          path="faq-legacy"
          element={
            <LegacyAdminScreen title="FAQ">
              <Faq />
            </LegacyAdminScreen>
          }
        />
        <Route
          path="parametres-legacy"
          element={
            <LegacyAdminScreen title="Paramètres">
              <Parametres />
            </LegacyAdminScreen>
          }
        />
      </Route>

      <Route path="*" element={<Navigate to="/login" replace />} />
    </Routes>
    </>
  );
}
