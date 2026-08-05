# Time Series Correction

*[Version française plus bas ↓](#-correction-de-séries-temporelles-français)*

Desktop application to interactively visualize and correct the variables
of a data file (csv / xlsx / parquet), with event overlays and saving to
`<name>_corrected.<extension>`.

Originally created for **BVECSM** (*Bassin Versant Expérimental Campus
Sainte-Marthe*, an experimental research watershed) to manually correct
environmental sensor time series (temperature, water level, soil moisture,
etc.) before further processing, but usable for any timestamped tabular
data. Author: Maxime Tarka. See [LICENSE](LICENSE) (MIT).

## Download (end users)

Download the latest ready-to-use archive from the
[Releases page](../../releases), unzip it anywhere, then double-click
`run_app.bat`. That's it — no Python installation, no PowerShell script to
run, nothing to build. The archive already contains everything needed
(embedded Python runtime + app).

## Installation (development / maintainers)

This repository contains the application source code (`app/`). The
embedded Python runtime and the development environment (`.venv/`) are
not versioned; the `.ps1` scripts below are for the maintainer building a
release, not for end users.

- **Windows, no Python installed**: run
  `powershell -ExecutionPolicy Bypass -File setup\setup_runtime.ps1` to
  download an embeddable Python and install dependencies into `runtime/`,
  then launch with `run_app.bat`.
- **With Python 3.12 already installed**: create a virtual environment and
  install the dependencies listed in `setup/requirements.txt`, then run
  `python app/main.py`.

To build a ready-to-share archive (embedded runtime, without dev files),
see `setup/package_app.ps1` and [RELEASING.md](RELEASING.md).

## Launching the application

Double-click the desktop shortcut **"Correction series temporelles"**,
or run `run_app.bat` directly.

## Opening a file

- **"Open a data file..."**: opens a data file (`.csv`, `.xlsx`,
  `.parquet`). The timestamp column is detected automatically (by column
  name, or by its data type).
- **"Time axis"**: shows which column is used as the X axis (time). It
  defaults to the automatically detected column, but you can pick any
  other column from the dropdown if the detection picked the wrong one.
  Whichever column is selected as the time axis is removed from the
  **"Variable"** list (it cannot be corrected as a variable itself).
- **"Open an events file..."**: opens an events file (punctual annotations
  or time periods), shown as an overlay on the plot.
- The **"Variable"** dropdown lists all variables available in the file;
  selecting one plots it.

## Plot display

- The **"Display"** dropdown lets you choose to show:
  - **Raw**: the raw curve (original data, never modified).
  - **Corrected**: the corrected curve (with applied edits).
  - **Both**: both curves overlaid.
- **"Show events"**: shows/hides event markers (vertical lines or colored
  bands) loaded from the events file. Hovering over an event shows its
  details in a tooltip.
- When hovering the mouse over the plot:
  - the cursor's **x; y** coordinates are shown in the top-right corner.
  - when the cursor is near a data point, a yellow marker appears on that
    point.
- Navigating the plot:
  - **click and drag** (left mouse button) to pan the view.
  - **scroll wheel** to zoom in/out.
  - **"Y range"**: lets you type a precise Y-axis range, applied with the
    **"Apply"** button.
  - **"Auto (data)"**: automatically fits the view to the data extent.
  - **"Previous view"**: returns to the previous view.

## Selecting points

The **"Selection"** toolbar offers several modes (only one active at a
time):

- **Point**: click on the plot to select the nearest data point.
- **X range**: an adjustable vertical band (drag its edges) selects all
  points within that time range.
- **Y range**: an adjustable horizontal band selects all points whose Y
  value falls within that range.
- **X/Y rectangle**: two clicks (two opposite corners) define a rectangle;
  all points inside it are selected.
- **"Clear selection"**: clears the current selection.

Selected points are highlighted as an overlay on the plot (a selection is
required to apply most corrections below).

## Applying a correction

In the **"Corrections"** panel, click the desired correction type to show
its parameter form, then click **"Apply"**:

- **Delete**: removes the selected points (sets them to `NaN`).
- **Replace with a value**: replaces the selected points with a fixed
  value.
- **Offset (+/-)**: adds (or subtracts) a constant value to the selected
  points.
- **Multiply**: multiplies the selected points by a factor.
- **Custom expression**: applies a math formula to the selected points.
  `x` represents the selected value(s). See [Expression syntax](#expression-syntax)
  below for the full list of supported operators and functions.
  - The **"Insert hovered value from the plot"** button directly inserts
    into the formula the Y value of the point hovered/clicked on the plot
    (handy for calibrating a correction from a value read off the plot).
- **Threshold / min-max range**: does not require a selection — scans the
  whole variable and acts on points whose value is outside (or inside) a
  `Minimum`/`Maximum` range. The action to apply (delete, replace, offset,
  multiply, expression) is chosen in the **"Action"** dropdown.

The **"Apply automatically to selection"** checkbox applies the armed
correction as soon as a new selection is made, without needing to click
"Apply" each time.

## Expression syntax

The **"Custom expression"** correction and the **"Threshold / min-max
range"** correction (when its action is set to "Custom expression") both
evaluate a standard Python/numpy formula. `x` is the selected value(s)
(a number or array), and `np` (numpy) is available for math functions.

| You want... | Write it as |
| --- | --- |
| Addition / subtraction | `x + 1`, `x - 3` |
| Multiplication / division | `x * 2`, `x / 2` |
| Power (e.g. x²) | `x**2` |
| Square root | `np.sqrt(x)` |
| Exponential (e^x) | `np.exp(x)` |
| Natural log (ln) | `np.log(x)` |
| Log base 10 | `np.log10(x)` |
| Log base 2 | `np.log2(x)` |
| Absolute value | `np.abs(x)` |
| Sine / cosine / tangent (radians) | `np.sin(x)`, `np.cos(x)`, `np.tan(x)` |
| Convert degrees to radians | `np.radians(x)` |
| Rounding | `np.round(x)`, `np.floor(x)`, `np.ceil(x)` |
| Combine operations (parentheses) | `(x - 3) / 2`, `np.exp(np.log(x) * 2)` |

Notes:

- `**` is the power operator (not `^`).
- Functions that aren't basic arithmetic must be prefixed with `np.`
  (e.g. `np.exp(x)`, not `exp(x)`).
- Standard operator precedence applies: `np.exp(x) + 1` computes
  `e^x + 1`, not `e^(x+1)` — use parentheses to be explicit:
  `np.exp(x + 1)`.

## Automatic detection (spikes / frozen values)

The **"Detection"** panel offers two automatic detectors:

- **Detect spikes**: finds punctual outliers (spikes), based on a sliding
  window and a z-score threshold.
- **Detect frozen (stuck) values**: finds runs of identical consecutive
  values (stuck sensor), based on a minimum run length and a tolerance.

For each detector:

1. Adjust the parameters if needed.
2. Click **"Detect"**: candidate points are highlighted on the plot and
   their count is shown (**"Candidates: N"**).
3. **"Select candidates"**: turns the detected candidates into a
   selection, so a correction (e.g. "Delete") can be applied to them.
4. **"Clear"**: clears the detection results.

## History and undo

The **"History"** panel lists all corrections applied to the current
variable, in order:

- **"Undo last correction"**: undoes the most recently applied correction.
- **"Delete selected correction"**: removes a specific correction from the
  history (even if it's not the last one); later corrections are
  automatically recomputed.
- **"Restore deleted correction"**: restores the last correction removed
  with the button above.
- **"Revert to raw data"**: undoes all corrections for the variable and
  reverts to the original raw data (with confirmation).

## Saving

The **"Save as"** dropdown lets you choose the output file format:
**Parquet (.parquet)**, **CSV (.csv)** or **Excel (.xlsx)**.

The **Save** button offers 3 outputs, each written to a different file next
to the opened file. Click the button itself to write all 3 at once, or open
its menu to write just one:

- **`<name>_corrected.<extension>`** ("diff"): only the rows that actually
  changed (a value equal to raw is never included), only the touched
  columns. This is the file meant to be uploaded to the website's
  manual-correction page.
- **`<name>_corrected_serie.<extension>`** ("series"): the full series (all
  rows), only the touched column(s) — for working on the series as a whole.
- **`<name>_corrected_full.<extension>`** ("full"): the full table, all
  columns, all rows — today's original save behavior.

- The original file is **never modified**.
- If an output file already exists (for the chosen format), the new
  corrections are merged with previously saved corrections for other
  variables in that same file.
- When re-opening a file (whether it's a `_corrected*.*` file or not), the
  "Raw" and "Corrected" curves always start identical: no previous
  correction is automatically pre-applied to the displayed "Corrected"
  curve.

## Light / dark mode

The **"Dark mode" / "Light mode"** button in the top bar switches the whole
interface's theme. The choice is remembered between sessions.

## Troubleshooting

- Application logs are in `app\logs\app.log`.
- Unhandled errors (crashes) are written to `app\logs\crash.log`.

---

# 🇫🇷 Correction de séries temporelles (français)

*[English version above ↑](#time-series-correction)*

Application desktop pour visualiser et corriger interactivement les
variables d'un fichier de données (csv / xlsx / parquet), avec
superposition d'événements et sauvegarde dans `<nom>_corrected.<extension>`.

Créée à l'origine pour le **BVECSM** (*Bassin Versant Expérimental Campus
Sainte-Marthe*, un bassin versant expérimental de recherche) pour corriger
manuellement des séries temporelles de capteurs environnementaux
(température, niveau d'eau, humidité du sol, etc.) avant traitement, mais
utilisable pour tout jeu de données tabulaires horodatées. Auteur : Maxime
Tarka. Voir [LICENSE](LICENSE) (MIT).

## Télécharger (utilisateurs finaux)

Télécharger la dernière archive prête à l'emploi depuis la
[page Releases](../../releases), la décompresser n'importe où, puis
double-cliquer sur `run_app.bat`. C'est tout — pas d'installation de
Python, pas de script PowerShell à exécuter, rien à compiler. L'archive
contient déjà tout le nécessaire (runtime Python embarqué + application).

## Installation (développement / mainteneurs)

Ce dépôt contient le code source de l'application (`app/`). Le runtime
Python embarqué et l'environnement de développement (`.venv/`) ne sont pas
versionnés ; les scripts `.ps1` ci-dessous sont pour le mainteneur qui
prépare une release, pas pour les utilisateurs finaux.

- **Windows, sans Python installé** : exécuter
  `powershell -ExecutionPolicy Bypass -File setup\setup_runtime.ps1` pour
  télécharger un Python embarqué et installer les dépendances dans
  `runtime/`, puis lancer avec `run_app.bat`.
- **Avec Python 3.12 déjà installé** : créer un environnement virtuel et
  installer les dépendances listées dans `setup/requirements.txt`, puis
  lancer `python app/main.py`.

Pour créer une archive prête à distribuer (runtime embarqué, sans les
fichiers de dev), voir `setup/package_app.ps1` et
[RELEASING.md](RELEASING.md).

## Lancer l'application

Double-cliquer sur le raccourci Bureau **"Correction series temporelles"**,
ou directement sur `run_app.bat`.

## Ouvrir un fichier

- **"Open a data file..."** : ouvre un fichier de données (`.csv`, `.xlsx`,
  `.parquet`). La colonne de temps est détectée automatiquement (par nom
  de colonne, ou par son type de données).
- **"Time axis"** : indique quelle colonne est utilisée comme axe X
  (temps). Par défaut, c'est la colonne détectée automatiquement, mais on
  peut choisir n'importe quelle autre colonne dans le menu si la
  détection automatique s'est trompée. La colonne sélectionnée comme axe
  X est retirée de la liste **"Variable"** (elle ne peut pas être
  corrigée en tant que variable).
- **"Open an events file..."** : ouvre un fichier d'événements (annotations
  ponctuelles ou périodes), affichées en surimpression sur le graphe.
- Le menu **"Variable"** liste toutes les variables disponibles dans le
  fichier ; en choisir une affiche son graphe.

## Affichage du graphe

- Le menu **"Display"** permet de choisir d'afficher :
  - **Raw** : la courbe brute (données d'origine, jamais modifiées).
  - **Corrected** : la courbe corrigée (avec les modifications appliquées).
  - **Both** : les deux superposées.
- **"Show events"** : affiche/masque les marqueurs d'événements (lignes
  verticales ou bandes colorées) chargés depuis le fichier d'événements.
  Passer la souris sur un événement affiche son détail (infobulle).
- En passant la souris sur le graphe :
  - les coordonnées **x ; y** du curseur s'affichent dans le coin
    supérieur droit.
  - lorsque le curseur est proche d'un point de donnée, un marqueur jaune
    apparaît sur ce point.
- Navigation dans le graphe :
  - **glisser-déposer** (clic gauche maintenu) pour déplacer la vue.
  - **molette** pour zoomer/dézoomer.
  - **"Y range"** : permet de saisir manuellement un intervalle Y précis,
    avec un bouton **"Apply"**.
  - **"Auto (data)"** : recadre automatiquement la vue sur l'étendue des
    données.
  - **"Previous view"** : revient à la vue précédente.

## Sélectionner des points

La barre **"Selection"** propose plusieurs modes (un seul actif à la fois) :

- **Point** : clic sur le graphe pour sélectionner le point de donnée le
  plus proche.
- **X range** : une zone verticale ajustable (glisser ses bords) sélectionne
  tous les points dans cet intervalle de temps.
- **Y range** : une zone horizontale ajustable sélectionne tous les points
  dont la valeur Y est dans cet intervalle.
- **X/Y rectangle** : deux clics (deux coins opposés) définissent un
  rectangle ; tous les points à l'intérieur sont sélectionnés.
- **"Clear selection"** : efface la sélection courante.

Les points sélectionnés sont mis en évidence en surimpression sur le
graphe (la sélection est nécessaire pour appliquer la plupart des
corrections ci-dessous).

## Appliquer une correction

Dans le panneau **"Corrections"**, cliquer sur le type de correction
souhaité pour afficher son formulaire de paramètres, puis sur
**"Apply"** :

- **Delete** : supprime les points sélectionnés (mis à `NaN`).
- **Replace with a value** : remplace les points sélectionnés par une
  valeur fixe.
- **Offset (+/-)** : ajoute (ou soustrait) une valeur constante aux points
  sélectionnés.
- **Multiply** : multiplie les points sélectionnés par un facteur.
- **Custom expression** : applique une formule mathématique aux points
  sélectionnés. `x` représente la/les valeur(s) sélectionnée(s). Voir
  [Syntaxe des expressions](#syntaxe-des-expressions) ci-dessous pour la
  liste complète des opérateurs et fonctions disponibles.
  - Le bouton **"Insert hovered value from the plot"** insère directement
    dans la formule la valeur Y du point survolé/cliqué sur le graphe
    (pratique pour calibrer une correction à partir d'une valeur lue sur
    le graphe).
- **Threshold / min-max range** : ne nécessite pas de sélection — analyse
  toute la variable et agit sur les points dont la valeur est en dehors
  (ou à l'intérieur) d'un intervalle `Minimum`/`Maximum`. L'action à
  appliquer (suppression, remplacement, décalage, multiplication,
  expression) se choisit dans le menu **"Action"**.

La case **"Apply automatically to selection"** applique la correction
armée dès qu'une nouvelle sélection est faite, sans avoir à cliquer sur
"Apply" à chaque fois.

## Syntaxe des expressions

La correction **"Custom expression"** et la correction **"Threshold /
min-max range"** (lorsque son action est réglée sur "Custom expression")
évaluent toutes les deux une formule Python/numpy standard. `x` représente
la/les valeur(s) sélectionnée(s) (un nombre ou un tableau), et `np`
(numpy) est disponible pour les fonctions mathématiques.

| Pour faire... | Écrire... |
| --- | --- |
| Addition / soustraction | `x + 1`, `x - 3` |
| Multiplication / division | `x * 2`, `x / 2` |
| Puissance (ex. x²) | `x**2` |
| Racine carrée | `np.sqrt(x)` |
| Exponentielle (e^x) | `np.exp(x)` |
| Logarithme naturel (ln) | `np.log(x)` |
| Logarithme base 10 | `np.log10(x)` |
| Logarithme base 2 | `np.log2(x)` |
| Valeur absolue | `np.abs(x)` |
| Sinus / cosinus / tangente (radians) | `np.sin(x)`, `np.cos(x)`, `np.tan(x)` |
| Conversion degrés vers radians | `np.radians(x)` |
| Arrondi | `np.round(x)`, `np.floor(x)`, `np.ceil(x)` |
| Combiner des opérations (parenthèses) | `(x - 3) / 2`, `np.exp(np.log(x) * 2)` |

Remarques :

- `**` est l'opérateur de puissance (et non `^`).
- Les fonctions autres que les opérations arithmétiques de base doivent
  être préfixées par `np.` (ex. `np.exp(x)`, et non `exp(x)`).
- La priorité des opérateurs standard s'applique : `np.exp(x) + 1`
  calcule `e^x + 1`, et non `e^(x+1)` — utiliser des parenthèses pour
  être explicite : `np.exp(x + 1)`.

## Détection automatique (Spikes / valeurs figées)

Le panneau **"Detection"** propose deux détecteurs automatiques :

- **Detect spikes** : repère les valeurs aberrantes ponctuelles (pics),
  selon une fenêtre glissante et un seuil de z-score.
- **Detect frozen (stuck) values** : repère les séries de valeurs
  identiques (capteur figé), selon un nombre minimal de points consécutifs
  et une tolérance.

Pour chaque détecteur :

1. Ajuster les paramètres si besoin.
2. Cliquer sur **"Detect"** : les points candidats sont mis en évidence sur
   le graphe et leur nombre s'affiche (**"Candidates: N"**).
3. **"Select candidates"** : transforme les candidats détectés en
   sélection, pour pouvoir leur appliquer une correction (ex : "Delete").
4. **"Clear"** : efface les résultats de détection.

## Historique et annulation

Le panneau **"History"** liste toutes les corrections appliquées à la
variable courante, dans l'ordre :

- **"Undo last correction"** : annule la dernière correction appliquée.
- **"Delete selected correction"** : supprime une correction précise dans
  l'historique (même si elle n'est pas la dernière) ; les corrections
  suivantes sont automatiquement recalculées.
- **"Restore deleted correction"** : rétablit la dernière correction
  supprimée via le bouton précédent.
- **"Revert to raw data"** : annule toutes les corrections de la variable
  et revient aux données brutes d'origine (avec confirmation).

## Enregistrer

Le menu **"Save as"** permet de choisir le format du fichier de sortie :
**Parquet (.parquet)**, **CSV (.csv)** ou **Excel (.xlsx)**.

Le bouton **Save** propose 3 sorties, chacune écrite dans un fichier
différent à côté du fichier ouvert. Cliquer sur le bouton lui-même écrit
les 3 d'un coup, ou ouvrir son menu pour n'en écrire qu'une seule :

- **`<nom>_corrected.<extension>`** ("diff") : uniquement les lignes qui
  ont réellement changé (une valeur égale au brut n'est jamais incluse),
  uniquement les colonnes touchées. C'est le fichier destiné à être
  téléversé sur la page de correction manuelle du site web.
- **`<nom>_corrected_serie.<extension>`** ("series") : la série complète
  (toutes les lignes), uniquement la/les colonne(s) touchée(s) — pour
  travailler sur la série dans son ensemble.
- **`<nom>_corrected_full.<extension>`** ("full") : la table complète,
  toutes les colonnes, toutes les lignes — le comportement d'origine.

- Le fichier d'origine n'est **jamais modifié**.
- Si un fichier de sortie existe déjà (pour le format choisi), les
  nouvelles corrections sont fusionnées avec les corrections
  précédemment enregistrées pour les autres variables de ce même fichier.
- À la ré-ouverture d'un fichier (qu'il soit `_corrected*.*` ou non), les
  courbes "Raw" et "Corrected" démarrent toujours identiques : aucune
  correction précédente n'est pré-appliquée automatiquement à la courbe
  "Corrected" affichée.

## Mode clair / sombre

Le bouton **"Dark mode" / "Light mode"** dans la barre du haut bascule le
thème de toute l'interface. Le choix est mémorisé entre les sessions.

## Dépannage

- Les logs applicatifs sont dans `app\logs\app.log`.
- Les erreurs non gérées (crash) sont écrites dans `app\logs\crash.log`.
