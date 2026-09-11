// Union (déduplication par id) des <symbol> SVG définis dans les 6 maquettes
// HTML de référence (cedra-landing/login/admin/pme/acheteur/partenaire). Monté
// une seule fois à la racine de l'app ; chaque icône est ensuite référencée
// via <svg class="ic"><use href="#i-x"/></svg>, exactement comme la maquette.
const SPRITE_HTML = `
<symbol id="i-info" viewBox="0 0 24 24"><circle cx="12" cy="12" r="9"></circle><line x1="12" y1="16" x2="12" y2="12"></line><line x1="12" y1="8" x2="12.01" y2="8"></line></symbol>
<symbol id="i-alert" viewBox="0 0 24 24"><path d="M12 2 1 21h22z"></path><line x1="12" y1="9" x2="12" y2="13"></line><line x1="12" y1="17" x2="12.01" y2="17"></line></symbol>
<symbol id="i-grid" viewBox="0 0 24 24"><rect x="3" y="3" width="7" height="7"></rect><rect x="14" y="3" width="7" height="7"></rect><rect x="3" y="14" width="7" height="7"></rect><rect x="14" y="14" width="7" height="7"></rect></symbol>
<symbol id="i-file" viewBox="0 0 24 24"><path d="M6 2h9l5 5v15H6z"></path><path d="M15 2v5h5"></path></symbol>
<symbol id="i-card" viewBox="0 0 24 24"><rect x="2" y="5" width="20" height="14" rx="2"></rect><line x1="2" y1="10" x2="22" y2="10"></line></symbol>
<symbol id="i-return" viewBox="0 0 24 24"><polyline points="9 14 4 9 9 4"></polyline><path d="M20 20v-7a4 4 0 00-4-4H4"></path></symbol>
<symbol id="i-clipboard" viewBox="0 0 24 24"><path d="M9 3h6a1 1 0 011 1v2H8V4a1 1 0 011-1z"></path><rect x="5" y="5" width="14" height="16" rx="2"></rect></symbol>
<symbol id="i-bell" viewBox="0 0 24 24"><path d="M6 8a6 6 0 1112 0c0 7 3 9 3 9H3s3-2 3-9"></path><path d="M10.3 21a1.94 1.94 0 003.4 0"></path></symbol>
<symbol id="i-chart" viewBox="0 0 24 24"><line x1="12" y1="20" x2="12" y2="10"></line><line x1="18" y1="20" x2="18" y2="4"></line><line x1="6" y1="20" x2="6" y2="16"></line></symbol>
<symbol id="i-users" viewBox="0 0 24 24"><path d="M17 21v-2a4 4 0 00-4-4H7a4 4 0 00-4 4v2"></path><circle cx="9" cy="7" r="4"></circle><path d="M23 21v-2a4 4 0 00-3-3.87"></path><path d="M16 3.13a4 4 0 010 7.75"></path></symbol>
<symbol id="i-settings" viewBox="0 0 24 24"><circle cx="12" cy="12" r="3"></circle><path d="M19.4 15a1.65 1.65 0 00.33 1.82l.06.06a2 2 0 11-2.83 2.83l-.06-.06a1.65 1.65 0 00-1.82-.33 1.65 1.65 0 00-1 1.51V21a2 2 0 01-4 0v-.09A1.65 1.65 0 009 19.4a1.65 1.65 0 00-1.82.33l-.06.06a2 2 0 11-2.83-2.83l.06-.06A1.65 1.65 0 004.6 15a1.65 1.65 0 00-1.51-1H3a2 2 0 010-4h.09A1.65 1.65 0 004.6 9a1.65 1.65 0 00-.33-1.82l-.06-.06a2 2 0 112.83-2.83l.06.06A1.65 1.65 0 009 4.6a1.65 1.65 0 001-1.51V3a2 2 0 014 0v.09a1.65 1.65 0 001 1.51 1.65 1.65 0 001.82-.33l.06-.06a2 2 0 112.83 2.83l-.06.06A1.65 1.65 0 0019.4 9a1.65 1.65 0 001.51 1H21a2 2 0 010 4h-.09a1.65 1.65 0 00-1.51 1z"></path></symbol>
<symbol id="i-shield" viewBox="0 0 24 24"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"></path><polyline points="9 12 11 14 15 10"></polyline></symbol>
<symbol id="i-building" viewBox="0 0 24 24"><rect x="4" y="2" width="10" height="20" rx="1"></rect><rect x="14" y="9" width="6" height="13" rx="1"></rect><line x1="7" y1="6" x2="7" y2="6.01"></line><line x1="11" y1="6" x2="11" y2="6.01"></line><line x1="7" y1="10" x2="7" y2="10.01"></line><line x1="11" y1="10" x2="11" y2="10.01"></line><line x1="7" y1="14" x2="7" y2="14.01"></line><line x1="11" y1="14" x2="11" y2="14.01"></line></symbol>
<symbol id="i-cart" viewBox="0 0 24 24"><circle cx="9" cy="21" r="1"></circle><circle cx="20" cy="21" r="1"></circle><path d="M1 1h4l2.68 13.39a2 2 0 002 1.61h9.72a2 2 0 002-1.61L23 6H6"></path></symbol>
<symbol id="i-bank" viewBox="0 0 24 24"><line x1="3" y1="22" x2="21" y2="22"></line><line x1="6" y1="18" x2="6" y2="11"></line><line x1="10" y1="18" x2="10" y2="11"></line><line x1="14" y1="18" x2="14" y2="11"></line><line x1="18" y1="18" x2="18" y2="11"></line><polygon points="12 2 21 9 3 9"></polygon></symbol>
<symbol id="i-coin" viewBox="0 0 24 24"><circle cx="12" cy="12" r="9"></circle><path d="M9.5 15c0 1.1 1.1 2 2.5 2s2.5-.7 2.5-1.7-1-1.5-2.5-1.9-2.5-.9-2.5-1.9S10.6 8 12 8s2.5.9 2.5 2"></path><line x1="12" y1="6.5" x2="12" y2="17.5"></line></symbol>
<symbol id="i-check-square" viewBox="0 0 24 24"><rect x="3" y="3" width="18" height="18" rx="2"></rect><polyline points="8 12 11 15 16 9"></polyline></symbol>
<symbol id="i-merge" viewBox="0 0 24 24"><path d="M6 3v6a4 4 0 004 4h4"></path><path d="M18 3v6a4 4 0 01-4 4"></path><circle cx="6" cy="19" r="2"></circle><circle cx="18" cy="19" r="2"></circle><line x1="6" y1="17" x2="6" y2="10"></line><line x1="18" y1="17" x2="18" y2="14"></line></symbol>
<symbol id="i-plus" viewBox="0 0 24 24"><line x1="12" y1="5" x2="12" y2="19"></line><line x1="5" y1="12" x2="19" y2="12"></line></symbol>
<symbol id="i-clock" viewBox="0 0 24 24"><circle cx="12" cy="12" r="9"></circle><polyline points="12 7 12 12 15 14"></polyline></symbol>
<symbol id="i-file-check" viewBox="0 0 24 24"><path d="M6 2h9l5 5v15H6z"></path><path d="M15 2v5h5"></path><polyline points="9 14 11 16 15 11"></polyline></symbol>
<symbol id="i-hourglass" viewBox="0 0 24 24"><path d="M6 2h12M6 22h12M6 2c0 6 6 6 6 10s-6 4-6 10M18 2c0 6-6 6-6 10s6 4 6 10"></path></symbol>
<symbol id="i-check-circle" viewBox="0 0 24 24"><path d="M22 11.08V12a10 10 0 11-5.93-9.14"></path><polyline points="22 4 12 14.01 9 11.01"></polyline></symbol>
<symbol id="i-search" viewBox="0 0 24 24"><circle cx="11" cy="11" r="8"></circle><line x1="21" y1="21" x2="16.65" y2="16.65"></line></symbol>
<symbol id="i-mail" viewBox="0 0 24 24"><path d="M4 4h16v16H4z"></path><path d="M4 6l8 7 8-7"></path></symbol>
<symbol id="i-check" viewBox="0 0 24 24"><polyline points="20 6 9 17 4 12"></polyline></symbol>
<symbol id="i-image" viewBox="0 0 24 24"><rect x="3" y="3" width="18" height="18" rx="2"></rect><circle cx="8.5" cy="8.5" r="1.5"></circle><path d="M21 15l-5-5L5 21"></path></symbol>
<symbol id="i-inbox" viewBox="0 0 24 24"><polyline points="22 12 16 12 14 15 10 15 8 12 2 12"></polyline><path d="M5.45 5.11L2 12v6a2 2 0 002 2h16a2 2 0 002-2v-6l-3.45-6.89A2 2 0 0016.76 4H7.24a2 2 0 00-1.79 1.11z"></path></symbol>
<symbol id="i-check-double" viewBox="0 0 24 24"><path d="M2 12l5 5L18 6"></path><path d="M9 17l1 1L21 7"></path></symbol>
<symbol id="i-clock-history" viewBox="0 0 24 24"><circle cx="12" cy="12" r="9"></circle><polyline points="12 7 12 12 15 14"></polyline></symbol>
<symbol id="i-wallet" viewBox="0 0 24 24"><path d="M21 12V7H5a2 2 0 010-4h14v4"></path><path d="M3 5v14a2 2 0 002 2h16v-5"></path><path d="M18 12a2 2 0 000 4h4v-4z"></path></symbol>
<symbol id="i-folder" viewBox="0 0 24 24"><path d="M22 19a2 2 0 01-2 2H4a2 2 0 01-2-2V5a2 2 0 012-2h5l2 3h9a2 2 0 012 2z"></path></symbol>
<symbol id="i-trending" viewBox="0 0 24 24"><polyline points="23 6 13.5 15.5 8.5 10.5 1 18"></polyline><polyline points="17 6 23 6 23 12"></polyline></symbol>
<symbol id="i-percent" viewBox="0 0 24 24"><line x1="19" y1="5" x2="5" y2="19"></line><circle cx="6.5" cy="6.5" r="2.5"></circle><circle cx="17.5" cy="17.5" r="2.5"></circle></symbol>
<symbol id="i-back" viewBox="0 0 24 24"><line x1="19" y1="12" x2="5" y2="12"></line><polyline points="12 19 5 12 12 5"></polyline></symbol>
<symbol id="i-x" viewBox="0 0 24 24"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></symbol>
`;

export function IconSprite() {
  return (
    <svg style={{ display: "none" }} aria-hidden="true" dangerouslySetInnerHTML={{ __html: SPRITE_HTML }} />
  );
}
