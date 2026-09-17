"""
pages/1_Abonnes_vs_occasionnels.py — Page 2/3 : QUAND la demande arrive-t-elle ?

Message : les abonnés font les pics des heures de bureau, du lundi au vendredi ;
          les occasionnels roulent surtout l'après-midi. Les pics sont donc
          réguliers et prévisibles, ce qui permet de planifier les tournées.

Visualisation : abonnés vs occasionnels, heure par heure.
(La carte de chaleur heure × jour a été déplacée sur la page Synthèse, app.py.)
"""

import altair as alt
import streamlit as st

import utils as u

st.set_page_config(page_title="Vélos · Abonnés vs occasionnels", page_icon="🚲", layout="wide")
u.appliquer_style()

# --- Données et filtres (les mêmes que sur la synthèse) --------------------------
df, filtres = u.sidebar_filters(u.load_data())
if df.empty:
    u.message_vide()
    st.stop()

# --- Calcul du chiffre du titre -------------------------------------------------------
# Heures de pointe = 7h–9h et 16h–19h. On mesure la part des abonnés sur ces heures.
heures_pointe = [7, 8, 9, 16, 17, 18, 19]
pointe = df[df["heure"].isin(heures_pointe)]
part_pointe = pointe["registered"].sum() / pointe["count"].sum()

# La fin du titre dépend du chiffre : avec le filtre « week-end », les abonnés
# pèsent moins, et le titre ne doit pas continuer à dire « presque toutes ».
if part_pointe >= 0.85:
    fin_titre = "font presque toutes les locations"
elif part_pointe >= 0.5:
    fin_titre = "font la majorité des locations"
else:
    fin_titre = "ne sont plus majoritaires"

u.titre_minto(
    kicker="Vélos en libre-service · 2/3 · Quand ?",
    icone="clock",
    ligne1=f"Aux heures de pointe, les {u.mot('abonnés', u.VERT)}",
    ligne2=fin_titre,
    pastille=u.pct(part_pointe),
    couleur=u.VERT,
    sous_titre="Part des abonnés dans les locations de 7h–9h et 16h–19h. "
               "Des usagers réguliers : la demande de pointe est prévisible d'un jour à l'autre.",
    filtres=filtres,
)

# =====================================================================================
# Abonnés vs occasionnels, heure par heure
# (une seule visualisation sur cette page : pas besoin d'onglets)
# =====================================================================================
# Moyenne par heure des deux types d'usagers
usagers = df.groupby("heure", as_index=False)[["registered", "casual"]].mean()
# melt : on passe d'un tableau « large » (2 colonnes) à un tableau « long »
# (une colonne usager + une colonne valeur), le format attendu par Altair
usagers = usagers.melt(id_vars="heure", var_name="usager", value_name="locations")
usagers["usager"] = usagers["usager"].map({"registered": "Abonnés", "casual": "Occasionnels"})
usagers["Heure"] = usagers["heure"].astype(str) + "h"
usagers["Locations/h"] = usagers["locations"].map(u.nb)

# Heure de pic de chaque type d'usager, pour le sous-titre et les étiquettes
pics = usagers.loc[usagers.groupby("usager")["locations"].idxmax()]
pic_abo = pics[pics["usager"] == "Abonnés"].iloc[0]
pic_occ = pics[pics["usager"] == "Occasionnels"].iloc[0]
st.markdown(
    f"#### Les abonnés culminent à {int(pic_abo['heure'])}h, "
    f"les occasionnels à {int(pic_occ['heure'])}h"
)
st.caption("Deux usages différents : le trajet domicile-travail et la balade.")

# Couleurs fixes des deux entités : vert = abonnés, orange = occasionnels,
# sur TOUTES les pages. Deux séries → une légende, en plus des étiquettes.
couleurs = alt.Scale(domain=["Abonnés", "Occasionnels"], range=[u.VERT, u.ORANGE])

base = alt.Chart(usagers).encode(
    x=alt.X("heure:Q", title="Heure de la journée", scale=alt.Scale(domain=[0, 23], nice=False),
            axis=alt.Axis(values=list(range(0, 24, 3)), labelExpr="datum.value + 'h'", grid=False)),
    # Un seul axe Y pour les deux courbes : on compare des locations à des locations
    y=alt.Y("locations:Q", title="Locations par heure (moyenne)", scale=alt.Scale(zero=True)),
    color=alt.Color("usager:N", scale=couleurs),
)
lignes = base.mark_line(strokeWidth=2.5, strokeCap="round", strokeJoin="round")

# Survol au point le plus proche de la souris + trait vertical de repère
survol = alt.selection_point(fields=["heure"], nearest=True, on="pointerover", empty=False)
points = base.mark_point(size=90, filled=True).encode(
    opacity=alt.condition(survol, alt.value(1), alt.value(0)),
    tooltip=[alt.Tooltip("usager:N", title="Usager"), alt.Tooltip("Heure:N"), alt.Tooltip("Locations/h:N")],
).add_params(survol)
regle = alt.Chart(usagers).mark_rule(color=u.GRILLE).encode(x="heure:Q").transform_filter(survol)

# Étiquettes seulement au pic de chaque courbe, texte couleur encre.
# Le point porte un anneau de 2 px couleur du fond pour se détacher de la ligne.
pics = pics.assign(etiquette=pics["usager"] + " · " + pics["heure"].astype(str) + "h")
pics_points = alt.Chart(pics).mark_point(filled=True, size=110, stroke=u.FOND, strokeWidth=2).encode(
    x="heure:Q", y="locations:Q", color=alt.Color("usager:N", scale=couleurs, legend=None)
)
pics_textes = alt.Chart(pics).mark_text(dy=-16, fontSize=13, fontWeight=600, color=u.ENCRE).encode(
    x="heure:Q", y="locations:Q", text="etiquette:N"
)

graphique = alt.layer(regle, lignes, points, pics_points, pics_textes)
st.altair_chart(u.style_graphique(graphique, hauteur=360), use_container_width=True, theme=None)

with st.expander("Voir les données du graphique"):
    tableau = usagers.pivot(index="heure", columns="usager", values="locations").round(0)
    tableau.index = tableau.index.astype(str) + "h"
    st.dataframe(tableau, use_container_width=True)

# --- À retenir ---------------------------------------------------------------------------
u.encadre(
    "Les pics de semaine viennent d'usagers réguliers : on peut <b>fixer des tournées de "
    "rééquilibrage à heure fixe</b> (avant 7h et avant 16h) plutôt que de réagir au cas par cas. "
    "Le week-end, prévoir des vélos en début d'après-midi pour les occasionnels.",
    couleur=u.VERT,
)
