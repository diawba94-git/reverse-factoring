import { useState } from "react";
import { Link } from "react-router-dom";
import { Logo } from "../components/shell/Logo";
import "../styles/landing.css";

export function Landing() {
  const [menuOuvert, setMenuOuvert] = useState(false);

  return (
    <div className="cedra-landing">
      <header>
        <div className="wrap nav">
          <div className="nav-left">
            <Logo variant="full" size={50} />
            <nav className="nav-links">
              <a href="#comment-ca-marche">La solution</a>
              <a href="#pour-qui">Les acteurs</a>
              <a href="#faq">FAQ</a>
            </nav>
          </div>
          <div className="nav-right">
            <button
              type="button"
              className="mobile-menu-btn"
              aria-label="Ouvrir le menu"
              onClick={() => setMenuOuvert((v) => !v)}
            >
              <svg viewBox="0 0 24 24">
                <line x1="3" y1="6" x2="21" y2="6"></line>
                <line x1="3" y1="12" x2="21" y2="12"></line>
                <line x1="3" y1="18" x2="21" y2="18"></line>
              </svg>
            </button>
            <Link to="/login" className="btn">Se connecter</Link>
          </div>
        </div>
        <div className="wrap">
          <div className={`mobile-menu-panel ${menuOuvert ? "open" : ""}`}>
            <a href="#comment-ca-marche" onClick={() => setMenuOuvert(false)}>La solution</a>
            <a href="#pour-qui" onClick={() => setMenuOuvert(false)}>Les acteurs</a>
            <a href="#faq" onClick={() => setMenuOuvert(false)}>FAQ</a>
          </div>
        </div>
      </header>

      <section className="hero">
        <div className="wrap hero-grid">
          <div>
            <h1>La facture financée avant l'échéance.</h1>
            <p>Cedra relie le fournisseur, l'acheteur et un partenaire financier pour transformer une facture déjà validée en trésorerie immédiate — sans jamais détenir vos fonds.</p>
            <div className="hero-cta">
              <a href="#contact" className="btn">Prendre rendez-vous</a>
              <a href="#comment-ca-marche" className="btn btn-ghost">Voir comment ça marche</a>
            </div>
          </div>
          <div className="invoice-card">
            <div className="invoice-tag">Validée par l'acheteur</div>
            <div className="row"><span>Facture</span><span>FC-2608-041</span></div>
            <div className="row"><span>Montant</span><span>3 000 000 FCFA</span></div>
            <div className="row"><span>Échéance</span><span>90 jours</span></div>
            <div className="row"><span>Avance immédiate</span><span>80 %</span></div>
            <div className="row"><span>Solde après remboursement</span><span>20 % − frais</span></div>
            <div className="total"><span>Net perçu</span><span className="amount">2 910 000 FCFA</span></div>
          </div>
        </div>
      </section>

      <section style={{ padding: "70px 0 20px" }}>
        <div className="wrap">
          <div className="section-head">
            <p className="kicker">Nos promesses chez Cedra</p>
            <h2>Ce que vous gagnez en travaillant avec nous.</h2>
          </div>
          <div className="promesses-grid">
            <div className="promesse-item">
              <div className="p-icon">
                <svg viewBox="0 0 24 24"><rect x="2" y="5" width="20" height="14" rx="2"></rect><line x1="2" y1="10" x2="22" y2="10"></line></svg>
              </div>
              <h3>Jusqu'à 98% du net versé</h3>
              <p>80% dès la décision du partenaire, le solde après remboursement — pour un taux total qui reste sous 3%, quelle que soit la durée.</p>
            </div>
            <div className="promesse-item">
              <div className="p-icon">
                <svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="9"></circle><polyline points="12 7 12 12 15 14"></polyline></svg>
              </div>
              <h3>Décision sous 24h</h3>
              <p>Le partenaire financier répond rapidement — vous savez où vous en êtes sans attendre des semaines.</p>
            </div>
            <div className="promesse-item">
              <div className="p-icon">
                <svg viewBox="0 0 24 24"><path d="M9 12l2 2 4-4"></path><circle cx="12" cy="12" r="9"></circle></svg>
              </div>
              <h3>Fini les relances gênantes</h3>
              <p>Une fois la facture financée, c'est le partenaire qui gère l'échéance — vous n'avez plus à relancer votre client.</p>
            </div>
            <div className="promesse-item">
              <div className="p-icon">
                <svg viewBox="0 0 24 24"><path d="M20 12a8 8 0 11-3-6.2"></path><path d="M20 4v5h-5"></path></svg>
              </div>
              <h3>Aucun engagement minimum</h3>
              <p>Vous choisissez de financer ou non, facture par facture — pas de volume imposé, pas de caution exigée.</p>
            </div>
          </div>
        </div>
      </section>

      <section id="pour-qui">
        <div className="wrap">
          <div className="section-head">
            <p className="kicker">Les acteurs</p>
            <h2>Chacun garde son rôle. Cedra orchestre la transaction.</h2>
          </div>

          <div className="persona">
            <div className="p-text">
              <p className="p-label">Fournisseur</p>
              <h3>Émettez la facture, choisissez de la financer ou non.</h3>
              <p>Créez votre facture en quelques lignes ou importez-la. Une fois validée par votre client, décidez facture par facture si vous voulez être payé immédiatement.</p>
            </div>
            <div className="p-visual">
              <div className="bar fill"></div>
              <div className="bar fill2"></div>
              <div className="bar"></div>
            </div>
          </div>

          <div className="persona reverse">
            <div className="p-text">
              <p className="p-label">Acheteur</p>
              <h3>Allongez vos délais de paiement, sans fragiliser vos fournisseurs.</h3>
              <p>Vos fournisseurs peuvent être payés immédiatement via Cedra — vous pouvez donc négocier des délais de paiement plus longs sans nuire à leur trésorerie, tout en gardant votre propre argent plus longtemps. Deux personnes distinctes de votre équipe valident chaque facture ; vous payez toujours 100% à l'échéance habituelle, juste à une autre destination.</p>
            </div>
            <div className="p-visual">
              <div className="stat">2 / 2</div>
              <p style={{ margin: 0, fontSize: "13.5px", color: "var(--muted)" }}>validations requises avant financement — vous gardez le contrôle</p>
            </div>
          </div>

          <div className="persona">
            <div className="p-text">
              <p className="p-label">Partenaire financier</p>
              <h3>Financez sur la base de l'acheteur, pas du fournisseur.</h3>
              <p>Le risque de crédit repose sur une entreprise déjà identifiée et solvable. Décidez en moins de 24h, avec un compte dédié par fournisseur.</p>
            </div>
            <div className="p-visual">
              <div className="stat">&lt; 24h</div>
              <p style={{ margin: 0, fontSize: "13.5px", color: "var(--muted)" }}>délai de décision</p>
            </div>
          </div>
        </div>
      </section>

      <section id="comment-ca-marche" style={{ background: "var(--paper-deep)" }}>
        <div className="wrap">
          <div className="section-head">
            <p className="kicker">La solution</p>
            <h2>De la facture à la trésorerie, en quatre étapes.</h2>
          </div>
          <div className="process">
            <div className="process-step">
              <p className="process-num">01</p>
              <h4>Facture créée</h4>
              <p>Saisie native avec plusieurs lignes d'articles, ou import d'un fichier existant.</p>
            </div>
            <div className="process-step">
              <p className="process-num">02</p>
              <h4>Double validation</h4>
              <p>Deux personnes distinctes côté acheteur confirment la facture, systématiquement.</p>
            </div>
            <div className="process-step">
              <p className="process-num">03</p>
              <h4>Décision du partenaire</h4>
              <p>Le financeur évalue la solvabilité de l'acheteur et répond sous 24h.</p>
            </div>
            <div className="process-step">
              <p className="process-num">04</p>
              <h4>Avance versée</h4>
              <p>80 % immédiatement, le solde une fois l'acheteur ayant remboursé à l'échéance.</p>
            </div>
          </div>
        </div>
      </section>

      <section>
        <div className="wrap trust">
          <div className="trust-copy">
            <p className="kicker">Ce qui protège chaque partie</p>
            <h2>Un modèle pensé pour qu'aucun acteur ne porte un risque qu'il ne maîtrise pas.</h2>
            <p>Cedra ne détient jamais les fonds : chaque virement transite directement entre le fournisseur, l'acheteur et le partenaire financier. La plateforme structure la donnée et la confiance, pas l'argent.</p>
          </div>
          <div className="stat-row">
            <div className="stat-item">
              <span className="num">2,3-3 %</span>
              <span className="label">Taux total dégressif selon la durée — jamais de surprise sur le coût.</span>
            </div>
            <div className="stat-item">
              <span className="num">60-90j</span>
              <span className="label">Fenêtre d'échéance éligible, conforme au plafond légal en vigueur.</span>
            </div>
            <div className="stat-item">
              <span className="num">NINEA</span>
              <span className="label">Seule pièce obligatoire — les entreprises individuelles sont éligibles.</span>
            </div>
          </div>
        </div>
      </section>

      <section>
        <div className="wrap">
          <div className="section-head">
            <p className="kicker">Ce qu'en disent nos utilisateurs</p>
            <h2>Un service pensé pour rassurer, pas seulement pour financer.</h2>
          </div>
          <div className="temoin-grid">
            <div className="temoin-card">
              <p className="temoin-quote">Depuis que Sonatel valide nos factures sur Cedra, on n'attend plus 90 jours pour recevoir notre trésorerie. Le simulateur avant de demander l'avance est très clair.</p>
              <div className="temoin-who">
                <div className="temoin-avatar">A</div>
                <div>
                  <p className="temoin-name">Aïssatou B.</p>
                  <p className="temoin-role">Gérante, Kalao Industries</p>
                </div>
              </div>
            </div>
            <div className="temoin-card">
              <p className="temoin-quote">Ce qui nous a convaincus côté acheteur, c'est qu'on ne change rien à notre façon de payer — juste une convention signée une fois, et la double validation nous protège bien.</p>
              <div className="temoin-who">
                <div className="temoin-avatar">M</div>
                <div>
                  <p className="temoin-name">Moussa D.</p>
                  <p className="temoin-role">Responsable achats, Baobab Fresh</p>
                </div>
              </div>
            </div>
            <div className="temoin-card">
              <p className="temoin-quote">Le fait que Cedra ne détienne jamais notre argent, et que tout transite directement avec la banque partenaire, a levé toutes nos réticences internes.</p>
              <div className="temoin-who">
                <div className="temoin-avatar">F</div>
                <div>
                  <p className="temoin-name">Fatou N.</p>
                  <p className="temoin-role">Directrice financière, Dakar Textile Solutions</p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section id="faq" style={{ background: "var(--paper-deep)" }}>
        <div className="wrap">
          <div className="section-head">
            <p className="kicker">FAQ</p>
            <h2>Ce qu'on nous demande le plus souvent.</h2>
          </div>
          <div className="faq">
            <details>
              <summary>Faut-il un RCCM pour utiliser Cedra ?</summary>
              <p>Non. Le NINEA suffit pour une entreprise individuelle ou un artisan. Le RCCM n'est demandé que pour les sociétés constituées (SARL, SA, GIE).</p>
            </details>
            <details>
              <summary>Cedra détient-il mon argent à un moment donné ?</summary>
              <p>Jamais. Cedra orchestre les instructions de paiement, mais les fonds transitent toujours directement entre votre entreprise, votre client et le partenaire financier.</p>
            </details>
            <details>
              <summary>Nous sommes l'acheteur : pourquoi accepter de changer le compte de paiement d'un fournisseur ?</summary>
              <p>C'est une inquiétude légitime — un changement de RIB non vérifié est un vecteur classique de fraude. C'est exactement pour cette raison qu'une convention signée par les trois parties (vous, votre fournisseur, le partenaire financier) encadre ce changement une seule fois, de façon tracée et vérifiable — bien plus sûr qu'un simple email de demande de changement de RIB.</p>
            </details>
            <details>
              <summary>Quel est l'intérêt pour nous, en tant qu'acheteur, si c'est notre fournisseur qui est payé plus vite ?</summary>
              <p>Un avantage direct : puisque votre fournisseur peut être payé immédiatement via Cedra, vous pouvez négocier des délais de paiement plus longs avec lui sans fragiliser sa trésorerie — ce qui améliore la vôtre, puisque vous gardez votre argent plus longtemps avant de le régler.</p>
            </details>
            <details>
              <summary>Que se passe-t-il si l'acheteur ne paie pas à l'échéance ?</summary>
              <p>Le risque est porté par le partenaire financier, jamais par le fournisseur qui a déjà reçu son avance. Un traitement de retard puis de contentieux est engagé par le partenaire.</p>
            </details>
            <details>
              <summary>Combien coûte réellement le service ?</summary>
              <p>Un taux total dégressif selon la durée de votre facture : environ 2,3 % pour une échéance de 60 jours, jusqu'à 3 % pour 90 jours. Ce taux couvre à la fois la commission Cedra et l'intérêt du partenaire financier — aucun autre frais caché.</p>
            </details>
            <details>
              <summary>Puis-je choisir de ne financer qu'une seule facture ?</summary>
              <p>Oui. Chaque facture validée peut être financée ou non, selon votre besoin de trésorerie du moment — aucun engagement de volume.</p>
            </details>
          </div>
        </div>
      </section>

      <section className="closing" id="contact">
        <div className="wrap">
          <div>
            <h2>Parlons de votre première facture.</h2>
            <p>Un échange de 20 minutes suffit pour vérifier votre éligibilité et celle de votre client.</p>
          </div>
          <a href="mailto:hello@cedra.io" className="btn">Prendre rendez-vous</a>
        </div>
      </section>

      <footer>
        <div className="wrap">
          <span>© 2026 Cedra — Affacturage inversé B2B, Sénégal</span>
          <div className="foot-links">
            <a href="#pour-qui">Les acteurs</a>
            <a href="#comment-ca-marche">La solution</a>
            <a href="#faq">FAQ</a>
          </div>
        </div>
      </footer>
    </div>
  );
}
