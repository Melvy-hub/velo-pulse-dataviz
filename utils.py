"""
utils.py — boîte à outils partagée par toutes les pages du dashboard.

Contenu :
  1. Les jetons de design (couleurs, polices) : un seul endroit pour les définir,
     donc une couleur garde le même sens sur toutes les pages.
  2. Le chargement des données, mis en cache avec @st.cache_data.
  3. Les filtres de la sidebar, partagés entre les pages.
  4. Les petits composants visuels : titre « Minto », tuile KPI, encadré.
  5. Le style commun des graphiques Altair.

Les jetons viennent du système de design « infographie storytelling »
(titre = conclusion, chiffre clé dans une pastille, une couleur par entité).
Ils sont recopiés ici plutôt qu'importés, pour que l'app marche aussi une fois
déployée en ligne, où le fichier d'origine n'existe pas.
"""

from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

# ---------------------------------------------------------------------------
# 1. Jetons de design
# ---------------------------------------------------------------------------

# Couleurs des données : UNE couleur = UNE signification dans tout le dashboard.
# Palette validée avec le script de la skill dataviz (lisible par les daltoniens).
BLEU = "#2a78d6"    # la demande de locations (mesure principale)
VERT = "#1baf7a"    # les abonnés
ORANGE = "#eb6834"  # les occasionnels

# Le vert est trop clair pour porter du TEXTE (contraste 2,7:1 sur le fond, il faut au moins 4,5:1).
# Pour les mots du titre, le kicker et la pastille, on utilise donc la même teinte en plus foncé.
# Les marques des graphiques (lignes, points) gardent le vert validé.
VERT_TEXTE = "#12805a"  # contraste 4,9:1
TEXTE_ACCENT = {VERT: VERT_TEXTE}  # couleur de texte à utiliser pour chaque couleur de données

# Couleurs de l'interface
FOND = "#FAF8F5"    # fond de page
PISTE = "#EFEDEA"   # fond des tuiles et des encadrés neutres
ENCRE = "#1C1C1C"   # texte principal
GRIS = "#6E6A66"    # légendes, textes secondaires
SOURCE = "#9A9591"  # texte discret (ligne « Filtres actifs »)
GRILLE = "#E3DFD9"  # lignes de grille : un cran seulement au-dessus du fond, pour rester discrètes

# Dossier du projet : on construit le chemin du CSV à partir de ce fichier,
# ainsi l'app trouve les données quel que soit le dossier d'où on la lance.
DOSSIER = Path(__file__).parent
FICHIER_DONNEES = DOSSIER / "data_velib.csv"

# Libellés français des codes numériques du dataset
# Attention : dans le dataset, la « saison 1 » (officiellement « printemps ») couvre en
# réalité janvier à mars (vérifié sur les dates). Pour ne pas tromper le lecteur, on
# nomme chaque saison par ses mois plutôt que par « printemps », « été », etc.
SAISONS = {1: "Janv.–mars", 2: "Avr.–juin", 3: "Juil.–sept.", 4: "Oct.–déc."}
METEOS = {1: "Clair", 2: "Nuageux", 3: "Pluie ou neige"}
JOURS = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]
JOUR_OUVRE = "Jour ouvré"
WEEK_END = "Week-end ou férié"


def tint(couleur, t):
    """Mélange une couleur avec le fond de page.

    Sert à « éteindre » ce qui n'est que du contexte : l'élément qui porte le
    message reste vif, les autres prennent la même teinte en pâle.
    La couleur reste présente, mais l'œil va d'abord vers l'élément vif
    (principe des canaux pré-attentifs).

    couleur : couleur hexadécimale, par ex. "#2a78d6"
    t       : 1 = couleur pleine, 0 = couleur du fond
    Renvoie une couleur hexadécimale.
    """
    # On lit les composantes rouge, vert, bleu (0–255) des deux couleurs
    c = [int(couleur[i:i + 2], 16) for i in (1, 3, 5)]
    f = [int(FOND[i:i + 2], 16) for i in (1, 3, 5)]
    # Moyenne pondérée composante par composante
    m = [round(fc * (1 - t) + cc * t) for cc, fc in zip(c, f)]
    return "#{:02x}{:02x}{:02x}".format(*m)


# Versions pâles utilisées pour le contexte
BLEU_PALE = tint(BLEU, 0.45)  # 0.45 plutôt que 0.38 : une ligne fine a besoin d'un peu plus d'encre qu'une barre


# ---------------------------------------------------------------------------
# Formats français
# ---------------------------------------------------------------------------

def nb(x):
    """Formate un nombre entier à la française : 1284.6 -> « 1 285 ».

    On utilise une espace insécable fine, pour que le nombre ne soit jamais coupé en fin de ligne.
    """
    return f"{round(x):,}".replace(",", " ")


def pct(x, signe=False):
    """Formate une proportion en pourcentage français : 0.418 -> « 42 % ».

    signe=True ajoute le signe devant (« +5 % », « −42 % »), utile pour un écart.
    Le signe moins est le vrai caractère typographique « − ».
    """
    valeur = round(x * 100)
    texte = f"{abs(valeur)} %"
    if signe:
        texte = ("+" if valeur > 0 else "−" if valeur < 0 else "") + texte
    return texte


# ---------------------------------------------------------------------------
# 2. Chargement des données
# ---------------------------------------------------------------------------

@st.cache_data
def load_data():
    """Lit le CSV et prépare les colonnes utiles au dashboard.

    @st.cache_data : Streamlit relance tout le script à chaque clic sur un filtre.
    Grâce au cache, le CSV n'est lu et transformé qu'une seule fois ; les clics
    suivants réutilisent le résultat gardé en mémoire.

    Renvoie un DataFrame avec, en plus des colonnes d'origine :
    heure, annee, jour_semaine, saison, meteo, type_jour.
    """
    # parse_dates convertit directement le texte « 2011-01-01 00:00:00 » en date
    df = pd.read_csv(FICHIER_DONNEES, parse_dates=["datetime"])

    # Découpage de la date en éléments exploitables
    df["heure"] = df["datetime"].dt.hour                          # 0 à 23
    df["annee"] = df["datetime"].dt.year                          # 2011 ou 2012
    df["jour_semaine"] = df["datetime"].dt.dayofweek.map(dict(enumerate(JOURS)))  # 0 = lundi

    # Codes numériques -> libellés lisibles
    df["saison"] = df["season"].map(SAISONS)
    # La météo 4 (orage, grêle) n'existe que sur UNE seule heure dans tout le
    # dataset : une moyenne sur 1 ligne ne veut rien dire, on la regroupe donc
    # avec la météo 3 (pluie ou neige). clip(upper=3) remplace 4 par 3.
    df["meteo"] = df["weather"].clip(upper=3).map(METEOS)
    # workingday = 1 pour un jour de semaine non férié
    df["type_jour"] = df["workingday"].map({1: JOUR_OUVRE, 0: WEEK_END})
    return df


# ---------------------------------------------------------------------------
# 3. Filtres de la sidebar
# ---------------------------------------------------------------------------

# Clés des widgets de filtre dans st.session_state
CLES_FILTRES = ["f_annees", "f_saisons", "f_type_jour", "f_meteos"]


def sidebar_filters(df):
    """Affiche les 4 filtres dans la sidebar et renvoie les données filtrées.

    Les filtres sont les mêmes sur toutes les pages et gardent leur valeur
    quand on change de page : un responsable qui regarde « l'été 2012 » ne doit
    pas perdre sa sélection en passant au détail.

    Renvoie (df_filtre, texte_filtres_actifs).
    """
    # Astuce Streamlit : quand on change de page, les valeurs des widgets qui
    # ne sont plus affichés sont effacées. Réécrire chaque valeur dans
    # session_state avant de recréer le widget la conserve.
    for cle in CLES_FILTRES:
        if cle in st.session_state:
            st.session_state[cle] = st.session_state[cle]

    with st.sidebar:
        st.markdown("### Filtres")

        # Listes des choix possibles, dans un ordre logique (pas alphabétique)
        annees = [int(a) for a in sorted(df["annee"].unique())]  # int() : entiers Python simples, plus propres à afficher
        saisons = list(SAISONS.values())
        meteos = list(METEOS.values())

        # Valeurs de départ (tout est sélectionné), posées une seule fois dans
        # session_state. On ne passe pas « default= » aux widgets : Streamlit
        # afficherait un avertissement si une valeur venait des deux côtés.
        st.session_state.setdefault("f_annees", annees)
        st.session_state.setdefault("f_saisons", saisons)
        st.session_state.setdefault("f_type_jour", "Tous")
        st.session_state.setdefault("f_meteos", meteos)

        # Filtre 1 : année(s)
        choix_annees = st.multiselect("Année", annees, key="f_annees")
        # Filtre 2 : saison(s)
        choix_saisons = st.multiselect("Saison", saisons, key="f_saisons")
        # Filtre 3 : type de jour. Un bouton radio, car on ne choisit qu'une seule option.
        choix_jour = st.radio(
            "Type de jour",
            ["Tous", JOUR_OUVRE, WEEK_END],
            key="f_type_jour",
        )
        # Filtre 4 : météo
        choix_meteos = st.multiselect("Météo", meteos, key="f_meteos")

        st.caption("Les chiffres, titres et graphiques se recalculent à chaque changement.")

    # Application des filtres : isin() garde les lignes dont la valeur est dans la sélection
    masque = (
        df["annee"].isin(choix_annees)
        & df["saison"].isin(choix_saisons)
        & df["meteo"].isin(choix_meteos)
    )
    if choix_jour != "Tous":
        masque &= df["type_jour"] == choix_jour

    # Petit résumé lisible, affiché sous le titre de chaque page : comme les
    # filtres sont dans la sidebar, on rappelle ici ce qui est sélectionné.
    def resume(choix, tous, nom):
        """Écrit « toutes les saisons » si tout est coché, sinon la liste choisie."""
        if len(choix) == len(tous):
            return nom
        return ", ".join(str(c) for c in choix) or "aucune sélection"

    texte = " · ".join([
        resume(choix_annees, annees, "2011–2012"),
        resume(choix_saisons, saisons, "toutes saisons"),
        "tous les jours" if choix_jour == "Tous" else choix_jour.lower(),
        resume(choix_meteos, meteos, "toutes météos"),
    ])
    return df[masque], texte


# ---------------------------------------------------------------------------
# 4. Composants visuels (HTML + CSS)
# ---------------------------------------------------------------------------

def appliquer_style():
    """Injecte les polices et le CSS commun à toutes les pages.

    - Poppins (Google Fonts) : police du système de design, lisible et ronde.
    - Font Awesome : icônes du kicker et des tuiles.
    - Les classes .titre, .pastille, .tuile, .encadre sont utilisées par les
      fonctions ci-dessous.
    """
    st.markdown(
        f"""<style>
@import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;600;700;800&display=swap');
@import url('https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.2/css/all.min.css');

/* Poppins uniquement sur les éléments de TEXTE (paragraphes, titres, libellés).
   On évite un sélecteur trop large du type [class*="st-"] : il changerait aussi la
   police des icônes de Streamlit (flèche du menu « Voir les données », barre d'outils
   du tableau). Ces icônes sont des mots comme « keyboard_arrow_down » dessinés avec une
   police spéciale : avec Poppins, le mot s'afficherait en toutes lettres par-dessus le texte. */
html, body, p, li, h1, h2, h3, h4, h5, h6, label,
[data-testid="stMarkdownContainer"], [data-testid="stWidgetLabel"],
.stTabs button, [data-baseweb="tag"] span {{ font-family: 'Poppins', sans-serif; }}
/* Sécurité : on rend explicitement leur police aux icônes Streamlit */
[data-testid="stIconMaterial"], .material-symbols-rounded, [class*="material-symbols"] {{
    font-family: 'Material Symbols Rounded' !important; }}
/* Les icônes Font Awesome gardent leur propre police, sinon elles s'affichent comme des carrés */
.fa-solid {{ font-family: 'Font Awesome 6 Free' !important; font-weight: 900; }}
.block-container {{ padding-top: 3.8rem; max-width: 1150px; }}

/* En-tête : bande d'accent à gauche + kicker + titre sur 2 lignes */
.entete {{ border-left: 6px solid; padding: 2px 0 2px 18px; margin-bottom: 6px; }}
.kicker {{ font-weight: 600; font-size: 0.8rem; letter-spacing: .06em; text-transform: uppercase; }}
.kicker i {{ margin-right: 6px; }}
.titre {{ font-weight: 800; font-size: 1.75rem; line-height: 1.3; color: {ENCRE}; margin: 4px 0 6px 0; }}
/* La pastille met le chiffre clé en avant : c'est la première chose que l'œil lit */
.pastille {{ display: inline-block; color: white; border-radius: 999px;
            padding: 0 14px; margin-left: 8px; font-size: 1.45rem; line-height: 1.55; vertical-align: 2px; }}
.sous-titre {{ color: {GRIS}; font-size: 0.95rem; margin: 0; }}
.filtres-actifs {{ color: {SOURCE}; font-size: 0.8rem; margin: 2px 0 14px 24px; }}
.filtres-actifs i {{ margin-right: 5px; }}

/* Tuile KPI : libellé discret, valeur en gros, contexte en dessous */
.tuile {{ background: white; border: 1px solid {PISTE}; border-radius: 14px; padding: 16px 18px; height: 100%; }}
.tuile-label {{ color: {GRIS}; font-size: 0.85rem; font-weight: 500; }}
.tuile-label .rond {{ display: inline-flex; align-items: center; justify-content: center; width: 26px; height: 26px;
                     border-radius: 50%; color: white; font-size: 0.7rem; margin-right: 8px; }}
.tuile-valeur {{ color: {ENCRE}; font-size: 2rem; font-weight: 700; line-height: 1.25; margin-top: 6px; }}
.tuile-contexte {{ color: {GRIS}; font-size: 0.82rem; }}

/* Encadrés : « À retenir » (action) et note d'honnêteté */
.encadre {{ border-radius: 14px; padding: 14px 18px; margin: 14px 0 6px 0; font-size: 0.92rem; color: {ENCRE}; }}
.encadre b.tete {{ display: block; margin-bottom: 2px; }}
</style>""",
        unsafe_allow_html=True,
    )


def mot(texte, couleur):
    """Renvoie un mot du titre coloré dans la couleur de son entité (ex. « abonnés » en vert)."""
    return f'<span style="color:{TEXTE_ACCENT.get(couleur, couleur)}">{texte}</span>'


def titre_minto(kicker, icone, ligne1, ligne2, pastille, couleur, sous_titre, filtres):
    """Affiche l'en-tête d'une page.

    Principe de Minto : le titre donne la CONCLUSION, pas le thème.
    « En semaine, la demande explose à 8h et 17h » plutôt que « Locations par heure ».

    kicker     : petit sur-titre (ex. « Vélos en libre-service · 1/3 »)
    icone      : nom d'une icône Font Awesome (ex. « bicycle »)
    ligne1/2   : les deux lignes du titre (peuvent contenir un mot())
    pastille   : chiffre clé affiché dans la pastille (ou None)
    couleur    : couleur d'accent de la page
    sous_titre : phrase d'explication sous le titre
    filtres    : texte des filtres actifs
    """
    # Si la couleur de la page est trop claire pour du texte, on prend sa version foncée
    couleur = TEXTE_ACCENT.get(couleur, couleur)
    # Les couleurs sont écrites directement sur chaque élément (style="...") :
    # Streamlit retire les variables CSS personnalisées du HTML affiché.
    bulle = f'<span class="pastille" style="background:{couleur}">{pastille}</span>' if pastille else ""
    st.markdown(
        f'<div class="entete" style="border-left-color:{couleur}">'
        f'<div class="kicker" style="color:{couleur}"><i class="fa-solid fa-{icone}"></i>{kicker}</div>'
        f'<div class="titre">{ligne1}<br>{ligne2}{bulle}</div>'
        f'<p class="sous-titre">{sous_titre}</p>'
        f"</div>"
        f'<p class="filtres-actifs"><i class="fa-solid fa-filter"></i>Filtres actifs : {filtres}</p>',
        unsafe_allow_html=True,
    )


def tuile_kpi(label, icone, couleur, valeur, contexte):
    """Affiche une tuile KPI : libellé + valeur + contexte.

    Un KPI sans contexte ne dit pas s'il est bon ou mauvais : la ligne de
    contexte donne toujours une comparaison (×N la moyenne, écart en %, évolution).
    Le texte reste couleur encre ; seule la pastille ronde de l'icône porte la
    couleur de l'entité (règle : le texte ne prend jamais la couleur des données).
    """
    st.markdown(
        f'<div class="tuile">'
        f'<div class="tuile-label"><span class="rond" style="background:{couleur}">'
        f'<i class="fa-solid fa-{icone}"></i></span>{label}</div>'
        f'<div class="tuile-valeur">{valeur}</div>'
        f'<div class="tuile-contexte">{contexte}</div>'
        f"</div>",
        unsafe_allow_html=True,
    )


def encadre(texte, genre="retenir", couleur=BLEU):
    """Affiche un encadré sous les graphiques.

    genre="retenir" : l'action à mener (fond teinté de la couleur de la page)
    genre="note"    : une précision d'honnêteté sur les données (fond neutre)
    """
    if genre == "retenir":
        fond, tete, icone = tint(couleur, 0.13), "À retenir", "lightbulb"
    else:
        fond, tete, icone = PISTE, "À savoir sur ces chiffres", "circle-info"
    st.markdown(
        f'<div class="encadre" style="background:{fond}">'
        f'<b class="tete"><i class="fa-solid fa-{icone}"></i>&nbsp; {tete}</b>{texte}</div>',
        unsafe_allow_html=True,
    )


def message_vide():
    """Message affiché quand les filtres ne laissent aucune donnée (au lieu d'une erreur)."""
    st.info("Aucune donnée ne correspond à ces filtres. Élargissez la sélection dans la barre latérale.")


# ---------------------------------------------------------------------------
# 5. Style commun des graphiques Altair
# ---------------------------------------------------------------------------

def style_graphique(chart, hauteur=340):
    """Applique le même habillage sobre à tous les graphiques.

    Règles appliquées :
    - police Poppins, textes en encre et gris (jamais dans la couleur des données) ;
    - grille en traits fins, pleins et très clairs : elle aide à lire sans attirer l'œil ;
    - pas de cadre autour du graphique (de l'encre qui ne porte aucune donnée) ;
    - légende en haut, là où l'œil arrive en premier.
    """
    return (
        chart.properties(height=hauteur, background="transparent")
        .configure(font="Poppins")
        .configure_view(strokeWidth=0)  # pas de cadre
        .configure_axis(
            labelColor=GRIS, titleColor=GRIS, labelFontSize=12, titleFontSize=12,
            titleFontWeight=500, gridColor=GRILLE, gridWidth=1, domainColor=GRILLE,
            tickColor=GRILLE, labelPadding=6, titlePadding=10,
        )
        .configure_legend(
            orient="top", title=None, labelColor=ENCRE, labelFontSize=12,
            symbolStrokeWidth=3, symbolSize=180,
        )
    )
