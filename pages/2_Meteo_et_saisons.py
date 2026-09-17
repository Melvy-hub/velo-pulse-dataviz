"""
pages/2_Meteo_et_saisons.py — Page 3/3 : POURQUOI la demande varie-t-elle ?

Message : la météo pilote la demande. La pluie la fait chuter d'environ 40 %,
          le froid la divise, l'été et la chaleur la font monter.
          Le responsable des opérations peut donc dimensionner ses équipes
          et la flotte à partir de la prévision météo.

Un onglet par visualisation :
  1. Locations selon la météo (barres horizontales)
  2. Locations selon la saison (colonnes)
  3. Locations selon la température (colonnes par tranche de 5 °C)
"""

import altair as alt
import pandas as pd
import streamlit as st

import utils as u

st.set_page_config(page_title="Vélos · Météo et saisons", page_icon="🚲", layout="wide")
u.appliquer_style()

# --- Données et filtres ---------------------------------------------------------------
df, filtres = u.sidebar_filters(u.load_data())
if df.empty:
    u.message_vide()
    st.stop()

# Moyenne par météo, gardée dans l'ordre logique Clair → Nuageux → Pluie.
# On garde aussi le nombre d'heures observées (size) : une moyenne calculée
# sur peu d'heures est moins fiable, on l'affiche dans l'infobulle.
meteo = (
    df.groupby("meteo")["count"].agg(moyenne="mean", heures="size")
    .reindex(list(u.METEOS.values()))   # ordre logique, pas alphabétique
    .dropna()                           # retire les météos exclues par les filtres
    .reset_index()
)

# Chiffre du titre : écart pluie / temps clair (seulement si les deux sont sélectionnés)
if {"Clair", "Pluie ou neige"} <= set(meteo["meteo"]):
    clair = meteo.loc[meteo["meteo"] == "Clair", "moyenne"].iloc[0]
    pluie = meteo.loc[meteo["meteo"] == "Pluie ou neige", "moyenne"].iloc[0]
    ecart = pluie / clair - 1
    pastille = u.pct(-ecart)            # « 42 % » : le verbe « chuter » porte déjà le sens de la baisse
    ligne1 = f"La {u.mot('pluie', u.BLEU)} fait chuter"
    ligne2 = "la demande de"
    sous_titre = "Écart entre les locations moyennes par heure sous la pluie et par temps clair."
else:
    ecart, pastille = None, None
    ligne1 = f"La {u.mot('météo', u.BLEU)} pèse"
    ligne2 = "sur la demande"
    sous_titre = "Cochez « Clair » et « Pluie ou neige » dans les filtres pour mesurer l'effet de la pluie."

u.titre_minto(
    kicker="Vélos en libre-service · 3/3 · Pourquoi ça varie ?",
    icone="cloud-sun-rain",
    ligne1=ligne1,
    ligne2=ligne2,
    pastille=pastille,
    couleur=u.BLEU,
    sous_titre=sous_titre + " Les onglets montrent aussi l'effet de la saison et de la température.",
    filtres=filtres,
)

onglet1, onglet2, onglet3 = st.tabs(["Météo", "Saisons", "Température"])


def barres(data, champ_categorie, champ_valeur, categorie_forte, ordre, horizontal, titre_axe):
    """Construit un graphique en barres « une barre mise en avant, les autres en pâle ».

    data             : DataFrame avec une ligne par barre
    champ_categorie  : colonne des catégories (ex. "meteo")
    champ_valeur     : colonne des valeurs (ex. "moyenne")
    categorie_forte  : la catégorie qui porte le message, affichée en bleu vif
    ordre            : ordre d'affichage des catégories
    horizontal       : True = barres horizontales, False = colonnes verticales
    titre_axe        : titre de l'axe des valeurs

    Choix de design :
    - les barres partent de 0 : leur longueur est proportionnelle à la valeur (honnêteté) ;
    - épaisseur limitée à 24 px, bout arrondi de 4 px, base carrée ;
    - la valeur est écrite au bout de chaque barre (il n'y en a que quelques-unes),
      en couleur encre et non en bleu.
    """
    data = data.copy()
    data["Valeur"] = data[champ_valeur].map(u.nb) + " /h"
    data["Heures observées"] = data["heures"].map(u.nb)

    # Une seule teinte : bleu vif pour la catégorie du message, bleu pâle pour le contexte
    couleur = alt.condition(
        alt.datum[champ_categorie] == categorie_forte,
        alt.value(u.BLEU),
        alt.value(u.tint(u.BLEU, 0.38)),
    )
    axe_valeur = alt.X if horizontal else alt.Y
    axe_categorie = alt.Y if horizontal else alt.X
    encodage = {
        ("x" if horizontal else "y"): axe_valeur(
            f"{champ_valeur}:Q", title=titre_axe, scale=alt.Scale(zero=True),
            axis=alt.Axis(grid=True),
        ),
        ("y" if horizontal else "x"): axe_categorie(
            f"{champ_categorie}:N", title=None, sort=ordre,
            axis=alt.Axis(labelAngle=0, labelFontSize=13, labelColor=u.ENCRE, grid=False),
        ),
    }
    base = alt.Chart(data).encode(**encodage)
    rectangles = base.mark_bar(size=24, cornerRadiusEnd=4).encode(
        color=couleur,
        tooltip=[
            alt.Tooltip(f"{champ_categorie}:N", title="Catégorie"),
            alt.Tooltip("Valeur:N", title="Locations moyennes"),
            alt.Tooltip("Heures observées:N"),
        ],
    )
    # Étiquette au bout de la barre : à droite (horizontal) ou au-dessus (vertical)
    if horizontal:
        textes = base.mark_text(align="left", dx=8, fontSize=13, fontWeight=600, color=u.ENCRE)
    else:
        textes = base.mark_text(baseline="bottom", dy=-6, fontSize=13, fontWeight=600, color=u.ENCRE)
    return alt.layer(rectangles, textes.encode(text="Valeur:N"))


# =====================================================================================
# Onglet 1 — Météo
# =====================================================================================
with onglet1:
    if ecart is not None:
        st.markdown(f"#### Par temps de pluie, {u.pct(-ecart)} de locations en moins que par temps clair")
    else:
        st.markdown("#### Locations moyennes selon la météo")
    st.caption("« Pluie ou neige » regroupe aussi les orages : ils n'apparaissent qu'une seule heure dans les données.")

    graphique = barres(meteo, "meteo", "moyenne", "Pluie ou neige", list(u.METEOS.values()),
                       horizontal=True, titre_axe="Locations par heure (moyenne)")
    st.altair_chart(u.style_graphique(graphique, hauteur=220), use_container_width=True, theme=None)

    with st.expander("Voir les données du graphique"):
        st.dataframe(meteo.round(0).rename(columns={"meteo": "Météo", "moyenne": "Locations/h", "heures": "Heures"}),
                     hide_index=True, use_container_width=True)

    # --- Note d'honnêteté : la pluie n'est-elle pas simplement plus fréquente l'hiver ou la nuit ? ---
    # Pour vérifier, on compare pluie et temps clair À SAISON ET HEURE ÉGALES :
    # pour chaque couple (saison, heure), on calcule l'écart pluie / clair,
    # puis on fait la moyenne de ces écarts, pondérée par le nombre d'heures de pluie.
    if ecart is not None:
        croise = df[df["meteo"].isin(["Clair", "Pluie ou neige"])]
        moyennes = croise.groupby(["saison", "heure", "meteo"])["count"].mean().unstack("meteo")
        nb_pluie = croise[croise["meteo"] == "Pluie ou neige"].groupby(["saison", "heure"]).size()
        ecarts = (moyennes["Pluie ou neige"] / moyennes["Clair"] - 1).dropna()
        poids = nb_pluie.reindex(ecarts.index)
        if poids.sum() > 0:
            ecart_controle = (ecarts * poids).sum() / poids.sum()
            u.encadre(
                "La pluie tombe plus souvent à certaines saisons et heures, ce qui pourrait fausser la "
                "comparaison. En comparant pluie et temps clair <b>à même saison et même heure</b>, "
                f"l'écart reste de <b>{u.pct(ecart_controle, signe=True)}</b> : l'effet vient bien de la pluie.",
                genre="note",
            )

# =====================================================================================
# Onglet 2 — Saisons
# =====================================================================================
with onglet2:
    saisons = (
        df.groupby("saison")["count"].agg(moyenne="mean", heures="size")
        .reindex(list(u.SAISONS.values())).dropna().reset_index()
    )
    # La saison la plus calme porte le message : c'est là qu'on peut alléger les équipes
    calme = saisons.loc[saisons["moyenne"].idxmin()]
    forte = saisons.loc[saisons["moyenne"].idxmax()]
    if len(saisons) > 1:
        rapport = f"{forte['moyenne'] / calme['moyenne']:.1f}".replace(".", ",")
        st.markdown(f"#### En {calme['saison'].lower()}, {rapport} fois moins de locations qu'en {forte['saison'].lower()}")
    else:
        st.markdown(f"#### En {calme['saison'].lower()} : {u.nb(calme['moyenne'])} locations/h en moyenne")
    st.caption("Saisons nommées par leurs mois : dans les données d'origine, la « saison 1 » "
               "couvre janvier à mars, les mois les plus froids.")

    graphique = barres(saisons, "saison", "moyenne", calme["saison"], list(u.SAISONS.values()),
                       horizontal=False, titre_axe="Locations par heure (moyenne)")
    st.altair_chart(u.style_graphique(graphique, hauteur=320), use_container_width=True, theme=None)

    with st.expander("Voir les données du graphique"):
        st.dataframe(saisons.round(0).rename(columns={"saison": "Saison", "moyenne": "Locations/h", "heures": "Heures"}),
                     hide_index=True, use_container_width=True)

# =====================================================================================
# Onglet 3 — Température
# =====================================================================================
with onglet3:
    # On ne trace PAS les 10 000 heures en nuage de points : illisible et impossible
    # à survoler. On regroupe les heures par tranche de 5 °C et on affiche la moyenne.
    bornes = [0, 5, 10, 15, 20, 25, 30, 35, 45]
    etiquettes = ["0–5 °C", "5–10 °C", "10–15 °C", "15–20 °C", "20–25 °C", "25–30 °C", "30–35 °C", "35 °C et +"]
    temp = df.assign(tranche=pd.cut(df["temp"], bornes, labels=etiquettes))
    temp = (
        temp.groupby("tranche", observed=True)["count"].agg(moyenne="mean", heures="size")
        .reset_index()
    )
    temp["tranche"] = temp["tranche"].astype(str)
    # Les tranches avec moins de 30 heures sont retirées : leur moyenne serait trop fragile
    temp = temp[temp["heures"] >= 30]

    if temp.empty:
        st.info("Pas assez d'heures observées avec ces filtres pour comparer les températures.")
    else:
        froide, chaude = temp.iloc[0], temp.loc[temp["moyenne"].idxmax()]
        rapport = f"{chaude['moyenne'] / froide['moyenne']:.1f}".replace(".", ",")
        st.markdown(f"#### À {chaude['tranche']}, {rapport} fois plus de locations qu'à {froide['tranche']}")
        st.caption("Chaque colonne = moyenne des heures observées dans cette tranche de température. "
                   "Les tranches de moins de 30 heures sont masquées.")

        graphique = barres(temp, "tranche", "moyenne", chaude["tranche"], etiquettes,
                           horizontal=False, titre_axe="Locations par heure (moyenne)")
        st.altair_chart(u.style_graphique(graphique, hauteur=320), use_container_width=True, theme=None)

        with st.expander("Voir les données du graphique"):
            st.dataframe(temp.round(0).rename(columns={"tranche": "Température", "moyenne": "Locations/h", "heures": "Heures"}),
                         hide_index=True, use_container_width=True)

# --- À retenir (fin de l'histoire : l'action) -----------------------------------------------
u.encadre(
    "Consulter la <b>prévision météo de la veille</b> pour dimensionner les équipes : "
    "moins de tournées les jours de pluie et par grand froid, "
    "renfort les journées chaudes de juillet à septembre, surtout aux heures de pointe."
)
