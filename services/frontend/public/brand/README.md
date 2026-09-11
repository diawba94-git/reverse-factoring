# Monogramme "C" — icône d'application mobile uniquement

`icon-app.svg` est le monogramme "C" (carré arrondi vert, lettre C ouverte) réservé
exclusivement à l'icône d'application mobile (App Store, Play Store, écran d'accueil,
notification push système).

**Règle stricte** : ce fichier n'est jamais importé ni référencé par le code web de ce
dépôt — ni comme favicon, ni comme icône de sidebar, ni comme composant partagé. C'est un
asset statique séparé, à exporter en PNG aux résolutions requises par chaque plateforme
(iOS : 1024×1024 App Store + jeu AppIcon.appiconset ; Android : 512×512 Play Store + jeu
mipmap adaptive-icon) au moment de la mise en place d'un projet mobile — cette conversion
n'a pas été faite ici faute de projet mobile dans ce dépôt.

L'icône double-chevron (`Logo` avec `variant="icon"`, dans `src/components/shell/Logo.tsx`)
reste la seule icône de marque utilisée sur le web (sidebars, favicon, avatar système) :
ne jamais la remplacer par ce monogramme, et ne jamais faire apparaître les deux dans un
même contexte.
