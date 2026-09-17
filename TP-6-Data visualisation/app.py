"""
app.py — Page 1/3 : SYNTHÈSE (point d'entrée : `streamlit run app.py`).

Le nom du fichier sert de libellé dans le menu de la sidebar : « app ».
Pas d'accent dans les noms de fichiers : ils posent problème selon les systèmes (Windows, Linux, Git, URL).

Audience : le responsable des opérations du service de vélos en libre-service.
Message   : la demande suit les trajets domicile-travail. En semaine, deux pics
            (≈ 8h et 17h) concentrent les locations, et la pluie les fait chuter.
            Il faut donc remettre des vélos en place juste avant ces pics.

Structure de la page (reprend le cadrage) :
  - en-tête  : titre qui donne la conclusion, chiffre clé dans une pastille
  - zone KPIs : 3 indicateurs, chacun avec une comparaison
  - zone détail : courbe heure par heure, puis carte de chaleur heure × jour,
                  qui réagissent aux filtres
  - encadré « À retenir » : l'action à mener
Les pages détaillées sont dans le dossier pages/.
"""

import altair as alt
import pandas as pd
import streamlit as st

import utils as u  # nos outils communs : données, filtres, couleurs, composants

# set_page_config doit être le tout premier appel Streamlit de la page
st.set_page_config(page_title="Vélos · Synthèse", page_icon="🚲", layout="wide")
u.appliquer_style()

# --- Données et filtres --------------------------------------------------------
df_complet = u.load_data()                        # lu une seule fois grâce au cache
df, filtres = u.sidebar_filters(df_complet)       # données filtrées + résumé des filtres

# Si les filtres ne laissent rien, on l'explique et on arrête la page proprement
if df.empty:
    u.message_vide()
    st.stop()

# --- Calculs ---------------------------------------------------------------------
# Profil horaire : nombre moyen de locations pour chaque heure (0h–23h),
# séparément pour les jours ouvrés et les week-ends.
# On prend la MOYENNE et non la somme : sinon une sélection plus longue
# (2 ans au lieu d'1) donnerait des chiffres plus gros sans que la demande
# ait réellement changé.
profil = df.groupby(["type_jour", "heure"], as_index=False)["count"].mean()


def pics_du_jour(p):
    """Trouve le pic du matin (5h–11h) et le pic du soir (15h–20h) d'un profil horaire.

    p : DataFrame avec les colonnes heure et count, pour un seul type de jour.
    Renvoie une liste de lignes (heure, count), une par pic trouvé.
    """
    pics = []
    for debut, fin in [(5, 11), (15, 20)]:
        creneau = p[p["heure"].between(debut, fin)]
        if not creneau.empty:
            # idxmax donne l'index de la ligne où count est maximal
            pics.append(creneau.loc[creneau["count"].idxmax()])
    return pics


ouvre = profil[profil["type_jour"] == u.JOUR_OUVRE]
weekend = profil[profil["type_jour"] == u.WEEK_END]

# Le titre dépend des données filtrées : si l'on ne garde que le week-end,
# il n'y a plus de pic à 8h et le titre doit le dire.
if not ouvre.empty:
    pics = pics_du_jour(ouvre)
    heures_pics = " et ".join(f"{int(p['heure'])}h" for p in pics)
    # Rapport entre le pic le plus haut et la moyenne de la journée : « ×2,8 »
    rapport = max(p["count"] for p in pics) / ouvre["count"].mean()
    ligne1 = f"En semaine, la {u.mot('demande', u.BLEU)} explose"
    ligne2 = f"à {heures_pics}"
    sous_titre = ("Les trajets domicile-travail font deux pics par jour ouvré. "
                  "Ce sont les moments où les stations risquent de se vider.")
else:
    pics = [weekend.loc[weekend["count"].idxmax()]]
    rapport = pics[0]["count"] / weekend["count"].mean()
    ligne1 = f"Le week-end, la {u.mot('demande', u.BLEU)} culmine"
    ligne2 = f"vers {int(pics[0]['heure'])}h"
    sous_titre = "Sans trajets domicile-travail, la demande forme une seule bosse en début d'après-midi."

# Formatage français du rapport : 2.8 -> « ×2,8 »
pastille = f"×{rapport:.1f}".replace(".", ",")

# --- En-tête -----------------------------------------------------------------------
u.titre_minto(
    kicker="Vélos en libre-service · 1/3 · Synthèse",
    icone="bicycle",
    ligne1=ligne1,
    ligne2=ligne2,
    pastille=pastille,
    couleur=u.BLEU,
    sous_titre=sous_titre + f" La pastille compare le pic à la moyenne de la journée ({pastille}).",
    filtres=filtres,
)

# --- Zone KPIs (3 indicateurs maximum, tous avec un contexte) ------------------------
col1, col2, col3 = st.columns(3)

# KPI 1 — Heure de pointe : dit QUAND renforcer le stock de vélos
par_heure = df.groupby("heure")["count"].mean()     # moyenne par heure, tous jours confondus
heure_pic = int(par_heure.idxmax())
ratio_pic = par_heure.max() / par_heure.mean()
with col1:
    u.tuile_kpi(
        label="Heure de pointe",
        icone="clock",
        couleur=u.BLEU,
        valeur=f"{heure_pic}h",
        contexte=(f"{u.nb(par_heure.max())} locations/h, "
                  f"soit ×{ratio_pic:.1f} la moyenne horaire".replace(".", ",")),
    )

# KPI 2 — Effet de la pluie : dit COMBIEN de vélos prévoir selon la météo
clair = df.loc[df["meteo"] == "Clair", "count"].mean()
pluie = df.loc[df["meteo"] == "Pluie ou neige", "count"].mean()
with col2:
    # mean() d'une sélection vide renvoie NaN : on vérifie que les deux météos sont présentes
    if clair == clair and pluie == pluie:          # NaN est le seul nombre différent de lui-même
        u.tuile_kpi(
            label="Effet de la pluie",
            icone="cloud-rain",
            couleur=u.BLEU,
            valeur=u.pct(pluie / clair - 1, signe=True),
            contexte=f"{u.nb(pluie)} locations/h sous la pluie, contre {u.nb(clair)} par temps clair",
        )
    else:
        u.tuile_kpi("Effet de la pluie", "cloud-rain", u.BLEU, "—",
                    "Cochez « Clair » et « Pluie ou neige » dans les filtres pour comparer")

# KPI 3 — Part des abonnés : les trajets réguliers, donc prévisibles
part_abonnes = df["registered"].sum() / df["count"].sum()
with col3:
    annees = sorted(df["annee"].unique())
    if len(annees) == 2:
        # Contexte = évolution d'une année sur l'autre
        parts = df.groupby("annee").apply(
            lambda g: g["registered"].sum() / g["count"].sum(), include_groups=False
        )
        contexte = f"{u.pct(parts.iloc[0])} en 2011 → {u.pct(parts.iloc[1])} en 2012 : des trajets réguliers, donc prévisibles"
    else:
        contexte = f"des locations en {annees[0]} : des trajets réguliers, donc prévisibles"
    u.tuile_kpi("Part des abonnés", "id-card", u.VERT, u.pct(part_abonnes), contexte)

st.write("")  # un peu d'air entre les KPIs et le graphique

# --- Zone détail : courbe heure par heure ------------------------------------------------
st.markdown("#### Locations moyennes par heure")

# Colonnes texte pour des infobulles au format français
profil["Heure"] = profil["heure"].astype(str) + "h"
profil["Locations/h"] = profil["count"].map(u.nb)

# Couleurs FIXÉES par type de jour (domain -> range) : si un filtre retire le
# week-end, le jour ouvré reste bleu vif. Jour ouvré = vif car il porte le
# message ; week-end = même bleu en pâle, car c'est seulement le point de comparaison.
couleurs = alt.Scale(domain=[u.JOUR_OUVRE, u.WEEK_END], range=[u.BLEU, u.BLEU_PALE])

base = alt.Chart(profil).encode(
    x=alt.X(
        "heure:Q",
        title="Heure de la journée",
        scale=alt.Scale(domain=[0, 23], nice=False),
        axis=alt.Axis(values=list(range(0, 24, 3)), labelExpr="datum.value + 'h'", grid=False),
    ),
    # zero=True : l'axe part de 0 pour ne pas exagérer les écarts entre les heures
    y=alt.Y("count:Q", title="Locations par heure (moyenne)", scale=alt.Scale(zero=True)),
    color=alt.Color("type_jour:N", scale=couleurs, legend=alt.Legend(orient="top")),
)

# Lignes fines aux extrémités arrondies. 2,5 px au lieu des 2 px de la règle :
# la courbe pâle du week-end reste ainsi visible sans devenir épaisse.
lignes = base.mark_line(strokeWidth=2.5, strokeCap="round", strokeJoin="round")

# Survol : la sélection « nearest » active le point le plus proche de la souris,
# pas besoin de viser pile la ligne (zone de survol confortable).
survol = alt.selection_point(fields=["heure"], nearest=True, on="pointerover", empty=False)
points_survol = base.mark_point(size=90, filled=True, opacity=0).encode(
    opacity=alt.condition(survol, alt.value(1), alt.value(0)),
    tooltip=[
        alt.Tooltip("type_jour:N", title="Type de jour"),
        alt.Tooltip("Heure:N"),
        alt.Tooltip("Locations/h:N"),
    ],
).add_params(survol)
# Trait vertical fin à l'heure survolée, pour lire les deux courbes à la même heure
regle = alt.Chart(profil).mark_rule(color=u.GRILLE, strokeWidth=1).encode(x="heure:Q").transform_filter(survol)

# Étiquettes directes SÉLECTIVES : uniquement sur les pics qui portent le message,
# jamais sur tous les points. Le texte reste couleur encre, pas bleu.
# On garde du profil les lignes (heure, type de jour) des pics trouvés plus haut
table_pics = profil.merge(
    pd.DataFrame([{"heure": int(p["heure"]), "type_jour": p["type_jour"]} for p in pics])
)
table_pics["etiquette"] = table_pics["heure"].astype(str) + "h · " + table_pics["count"].map(u.nb) + " /h"
pics_points = alt.Chart(table_pics).mark_point(
    filled=True, size=110, color=u.BLEU, stroke=u.FOND, strokeWidth=2  # anneau couleur du fond autour du point
).encode(x="heure:Q", y="count:Q")
pics_textes = alt.Chart(table_pics).mark_text(
    dy=-16, fontSize=13, fontWeight=600, color=u.ENCRE
).encode(x="heure:Q", y="count:Q", text="etiquette:N")

graphique = alt.layer(regle, lignes, points_survol, pics_points, pics_textes)
st.altair_chart(u.style_graphique(graphique, hauteur=360), use_container_width=True, theme=None)

# Vue tableau : les valeurs restent lisibles sans survol (accessibilité)
with st.expander("Voir les données du graphique"):
    tableau = profil.pivot(index="heure", columns="type_jour", values="count").round(0)
    tableau.index = tableau.index.astype(str) + "h"
    st.dataframe(tableau, use_container_width=True)

# --- Zone détail (suite) : carte de chaleur heure × jour de la semaine ---------------------
# Complète la courbe : elle montre que les pics de 8h et 17h se répètent chaque jour ouvré.
# Moyenne des locations pour chaque couple (jour de la semaine, heure)
# On garde aussi le nombre d'heures observées par case (size)
grille = df.groupby(["jour_semaine", "heure"], as_index=False)["count"].agg(count="mean", heures="size")
grille["Heure"] = grille["heure"].astype(str) + "h"
grille["Locations/h"] = grille["count"].map(u.nb)

# Case la plus chargée : sert au sous-titre (chiffre calculé, pas écrit à la main).
# On ne retient que les cases observées au moins 20 heures : avec le filtre
# « week-end ou férié », un mercredi n'apparaît que les jours fériés, et une
# moyenne sur 2 ou 3 heures ne doit pas devenir le message principal.
fiables = grille[grille["heures"] >= 20]
top = (fiables if not fiables.empty else grille).loc[lambda g: g["count"].idxmax()]
st.markdown(
    f"#### Le créneau le plus chargé : {top['jour_semaine'].lower()} à {int(top['heure'])}h "
    f"({u.nb(top['count'])} locations/h)"
)
st.caption("Plus la case est foncée, plus il y a de locations. Lisez les colonnes 8h et 17h–18h du lundi au vendredi.")
if st.session_state.get("f_type_jour") == u.WEEK_END:
    st.caption("Avec le filtre « Week-end ou férié », les lignes du lundi au vendredi ne contiennent "
               "que les jours fériés, donc peu d'heures : lisez-les avec prudence (voir l'infobulle).")

carte = alt.Chart(grille).mark_rect(
    # Contour couleur du fond = un espace de 2 px entre les cases (pas une bordure noire)
    stroke=u.FOND, strokeWidth=2, cornerRadius=3,
).encode(
    # :O = ordinal, une case par heure, dans l'ordre 0h → 23h
    x=alt.X("heure:O", title="Heure de la journée",
            axis=alt.Axis(labelExpr="datum.value + 'h'", labelAngle=0,
                          values=list(range(0, 24, 2)))),
    # sort=JOURS : lundi en haut, dimanche en bas (et non l'ordre alphabétique)
    y=alt.Y("jour_semaine:N", title=None, sort=u.JOURS),
    # Dégradé d'UNE seule teinte, du bleu très pâle au bleu foncé :
    # « plus foncé = plus de locations » se lit sans légende compliquée.
    # Pas d'arc-en-ciel, qui inventerait des paliers qui n'existent pas.
    color=alt.Color(
        "count:Q",
        title="Locations/h",
        scale=alt.Scale(range=[u.tint(u.BLEU, 0.08), "#12406f"], zero=True),
        legend=alt.Legend(orient="top", direction="horizontal", gradientLength=220, title="Locations/h"),
    ),
    tooltip=[
        alt.Tooltip("jour_semaine:N", title="Jour"),
        alt.Tooltip("Heure:N"),
        alt.Tooltip("Locations/h:N"),
        alt.Tooltip("heures:Q", title="Heures observées"),
    ],
)
st.altair_chart(u.style_graphique(carte, hauteur=300), use_container_width=True, theme=None)

with st.expander("Voir les données du graphique"):
    tableau = grille.pivot(index="jour_semaine", columns="heure", values="count").reindex(u.JOURS).round(0)
    st.dataframe(tableau, use_container_width=True)

# --- À retenir : l'action ---------------------------------------------------------------
if not ouvre.empty:
    # On recommande d'agir une heure AVANT chaque pic, pour que les vélos soient déjà en place
    avant = " et ".join(f"<b>avant {int(p['heure']) - 1}h</b>" for p in pics)
    u.encadre(
        f"Planifier le rééquilibrage des stations {avant} les jours ouvrés, "
        "et réduire les équipes les jours de pluie. Le détail par type d'usager "
        "est page 2, l'effet de la météo page 3."
    )
else:
    u.encadre(
        f"Le week-end, une seule tournée de rééquilibrage <b>avant {int(pics[0]['heure']) - 1}h</b> suffit : "
        "la demande monte progressivement et forme une seule bosse."
    )
