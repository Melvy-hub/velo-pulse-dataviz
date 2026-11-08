"""
app.py - AIGUILLAGE du dashboard (point d'entrée : `streamlit run app.py`).

Ce fichier n'est pas une page : il déclare les pages et leur nom dans le menu.

Pourquoi : sans st.navigation, Streamlit nomme chaque onglet du menu d'après
son nom de fichier, et le point d'entrée s'affichait donc « app ».
Avec st.Page(..., title=...), on choisit le nom affiché (avec accents),
tout en gardant des noms de fichiers sans accent.

app.py reste le fichier principal : rien à changer dans les réglages de
Streamlit Cloud (« Main file path » = app.py).

Choix technique : pas de st.set_page_config ici. Chaque page garde le sien
(titre de l'onglet du navigateur, icône, mise en page large). Avec la version
de Streamlit déployée (1.41.1), set_page_config ne peut être appelé qu'une
fois par exécution : l'appeler ici ET dans les pages provoquerait une erreur.
"""

from pathlib import Path

import streamlit as st

# Dossier des pages, construit à partir de l'emplacement de ce fichier :
# le chemin reste juste quel que soit le dossier d'où l'app est lancée.
PAGES = Path(__file__).parent / "pages"

# Une ligne par page, dans l'ordre du menu : (fichier, titre affiché).
# default=True sur la première : c'est elle qui s'ouvre à l'arrivée sur l'app.
pages = [
    st.Page(PAGES / "0_Synthese.py", title="Synthèse", default=True),
    st.Page(PAGES / "1_Abonnes_vs_occasionnels.py", title="Abonnés vs occasionnels"),
    st.Page(PAGES / "2_Meteo_et_saisons.py", title="Météo et saisons"),
]

# st.navigation affiche le menu dans la barre latérale et renvoie la page
# choisie par l'utilisateur ; run() exécute le code de cette page.
navigation = st.navigation(pages)
navigation.run()
