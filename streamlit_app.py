import streamlit as st

from streamlit_extras.switch_page_button import switch_page
from utils import set_page_config, sidebar_image, set_css, author_link
from st_pages import Page, show_pages

set_page_config()
sidebar_image()
set_css()
author_link()

show_pages(
    [
        Page("streamlit_app.py", "Home", "🏠"),
        Page("app_pages/Reference_dataset.py", "Reference dataset", "📈"),
        Page("app_pages/Phylogeny.py", "Phylogeny", "🧬"),
        Page("app_pages/Genotype_lineage.py", "Genotype lineage", "📊"),
    ]
)

st.title("TB gen: Explore _Mycobacterium tuberculosis_ complex")
st.markdown("---")


def buttons():
    bt1, bt2, bt3, mk = st.columns([1, 1, 1, 8])

    with bt1:
        genotype_user_data = st.button("Genotype VCF")
    with bt2:
        phylogeny = st.button("Explore Phylogeny")
    with bt3:
        dataset = st.button("Reference Dataset")

    if genotype_user_data:
        switch_page("genotype lineage")
    if phylogeny:
        switch_page("phylogeny")
    if dataset:
        switch_page("reference dataset")


buttons()
