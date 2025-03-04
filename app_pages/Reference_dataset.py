import logging
import geopandas
import numpy as np
import pandas as pd
import altair as alt
import streamlit as st
import leafmap.foliumap as leafmap

from pdbio.vcfdataframe import VcfDataFrame
from streamlit_extras.colored_header import colored_header
from st_aggrid import AgGrid, GridUpdateMode, GridOptionsBuilder
from streamlit_extras.add_vertical_space import add_vertical_space
from utils import set_page_config, sidebar_image, set_css, home_page, author_link


def page_info():
    st.markdown(
        "<h2 style='text-align: left; color: #7A3777;'><strong>Reference dataset of <em>Mycobacterium tuberculosis</em> complex isolates</strong></h2>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "\
           <a style='text-decoration: none' \
            href='#dataset'>\
            <span style='color: #7A3777; font-size: 20px; font-weight:bold'>&#x278A; </span><span style='color: #A65AA3; font-size: 20px; font-weight:bold'>Dataset</span></a>\
           \n<a style='text-decoration: none' \
            href='#statistics'>\
            <span style='color: #7A3777; font-size: 20px; font-weight:bold'>&#x278B; </span><span style='color: #A65AA3; font-size: 20px; font-weight:bold'>Statistics</span></a>\
           \n<a style='text-decoration: none' \
            href='#map-showing-the-distribution-of-samples'>\
            <span style='color: #7A3777; font-size: 20px; font-weight:bold'>&#x278C; </span><span style='color: #A65AA3; font-size: 20px; font-weight:bold'>Map</span></a>\
            \n___\
            ",
        unsafe_allow_html=True,
    )


@st.experimental_memo()
def convert_df_to_tsv(df):
    return df.to_csv(sep="\t", index=False).encode("utf-8")


@st.experimental_memo(show_spinner=False)
def convert_df_to_csv(df):
    return df.to_csv(index=False).encode("utf-8")


@st.experimental_memo
def load_dataset():
    df = pd.read_csv("./data/samples_data.tsv", sep="\t")
    return df


@st.experimental_memo
def load_country_shapes():
    df = geopandas.read_file("./data/world_countries.json")
    return df


@st.experimental_memo
def load_regions():
    df = pd.read_csv("./data/regions.csv", usecols=["name", "region"]).rename(
        columns={"region": "Region"}
    )
    return df


@st.experimental_memo
def load_country_coords():
    df = pd.read_csv("./data/countries.csv")
    return df


@st.experimental_memo(show_spinner=False)
def vcf_to_df(vcf_path):
    logging.getLogger("pdbio").setLevel(logging.WARNING)
    vcfdf = VcfDataFrame(path=vcf_path)
    vcfdf.df.index = vcfdf.df.index + 1
    return vcfdf.df


@st.experimental_memo
def sample_count():
    dataset = load_dataset()
    sm1, mock = st.columns([2, 5])
    with sm1:
        st.metric(
            label="Total Samples",
            value=int(dataset["Sample"].count()),
            help="""Number of currently availible samples in the dataset
                """,
        )
    with mock:
        pass


@st.experimental_memo
def get_mapping_data():
    dataset = load_dataset()
    country_shapes = load_country_shapes()
    regions = load_regions()
    countries = load_country_coords()
    smp_data = pd.merge(
        dataset[
            [
                "Sample",
                "Country of isolation",
                "level 1",
                "level 2",
                "level 3",
                "level 4",
                "level 5",
            ]
        ],
        countries,
        how="left",
        left_on="Country of isolation",
        right_on="name",
    ).drop(columns=["country"])
    smp_data = smp_data[smp_data["name"].notna()]
    smp_data = pd.merge(left=smp_data, right=regions, how="left", on="name").drop(
        columns=["name"]
    )
    # Calculate number of samples per country
    cnt_samples = (
        dataset[["Sample", "Country of isolation"]]
        .groupby(["Country of isolation"])
        .count()
        .reset_index()
        .rename(columns={"Sample": "Number of Samples", "country of isolation": "name"})
    )
    # Merge country shapes and counts data
    cnt_samples_poly = (
        pd.merge(
            country_shapes,
            cnt_samples,
            left_on="name",
            right_on="Country of isolation",
            how="left",
        )
        .dropna()
        .drop(columns=["id", "Country of isolation"])
        .rename(columns={"name": "Country"})
    )
    cnt_samples_poly["Number of Samples"] = cnt_samples_poly[
        "Number of Samples"
    ].astype(np.int64)
    return smp_data, cnt_samples_poly


@st.experimental_singleton
def get_map():
    smp_data, cnt_samples_poly = get_mapping_data()
    m = leafmap.Map(
        layers_control=False,
        draw_control=False,
        measure_control=False,
        fullscreen_control=False,
        attribution_control=True,
    )
    m.add_basemap("CartoDB.PositronNoLabels")
    m.add_data(
        data=cnt_samples_poly,
        column="Number of Samples",
        layer_name="Number of Samples",
        k=9,
        add_legend=False,
    )
    m.add_points_from_xy(
        smp_data,
        layer_name="Samples",
        x="longitude",
        y="latitude",
        popup=[
            "Sample",
            "Country of isolation",
            "Region",
            "level 1",
            "level 2",
            "level 3",
            "level 4",
            "level 5",
        ],
        color_column="Region",
        icon_names=["star"],
        spin=True,
        add_legend=False,
    )
    return m


def show_dataset():
    dataset = load_dataset()
    gd = GridOptionsBuilder.from_dataframe(
        dataset, enableRowGroup=True, enableValue=True, enablePivot=True
    )
    gd.configure_grid_options(domLayout="normal", autoHeight=True)
    gd.configure_selection(selection_mode="multiple", use_checkbox=True)
    gd.configure_default_column(editable=False, groupable=True)
    gd.configure_side_bar()

    if st.checkbox("Show Dataset"):
        grid1 = AgGrid(
            dataset,
            gridOptions=gd.build(),
            enable_enterprise_modules=False,
            allowDragFromColumnsToolPanel=True,
            update_mode=GridUpdateMode.SELECTION_CHANGED,
            allow_unsafe_jscode=True,
            height=600,
            width="100%",
            theme="alpine",
        )
        tsv = convert_df_to_tsv(dataset)
        csv = convert_df_to_csv(dataset)

        dwn1, dwn2, mock = st.columns([1, 1, 4])

        with dwn1:
            st.download_button(
                label="💾 Download dataset as TSV",
                data=tsv,
                file_name="dataset.tsv",
                mime="text/csv",
            )
        with dwn2:
            st.download_button(
                label="💾 Download dataset as CSV",
                data=csv,
                file_name="dataset.csv",
                mime="text/csv",
            )
        with mock:
            pass

        sel_row = grid1["selected_rows"]
        dataset_sel = pd.DataFrame(sel_row)
        st.subheader("Selected Samples")
        # Grid 2
        builder = GridOptionsBuilder.from_dataframe(dataset_sel)
        builder.configure_column("_selectedRowNodeInfo", hide=True)
        go = builder.build()
        AgGrid(
            dataset_sel,
            gridOptions=go,
            domLayout="autoHeight",
            theme="alpine",
            enable_enterprise_modules=False,
        )
        try:
            dataset_sel = dataset_sel.drop(columns=["_selectedRowNodeInfo"])
        except KeyError:
            st.info("Select samples from the main dataframe", icon="ℹ️")
        tsv_sel = convert_df_to_tsv(dataset_sel)
        csv_sel = convert_df_to_csv(dataset_sel)

        dwn_sel1, dwn_sel2, mock_sel = st.columns([1, 1, 4])

        if dataset_sel.empty:
            st.warning("Subset dataframe is empty", icon="⚠️")
        else:
            with dwn_sel1:
                st.download_button(
                    label="💾 Download subset as TSV",
                    data=tsv_sel,
                    file_name="subsetted_dataset.tsv",
                    mime="text/csv",
                )
            with dwn_sel2:
                st.download_button(
                    label="💾 Download subset as CSV",
                    data=csv_sel,
                    file_name="subsetted_dataset.csv",
                    mime="text/csv",
                )
            with mock:
                pass

        return grid1


@st.experimental_memo(experimental_allow_widgets=True, show_spinner=False)
def sample_stats():
    dataset = load_dataset()
    # Dataframe filter
    sample_filter = st.selectbox("Select Sample", pd.unique(dataset["Sample"]))
    dataset = dataset[dataset["Sample"] == sample_filter]
    add_vertical_space(2)

    if st.checkbox("Show Variants"):
        with st.spinner("Loading VCF..."):
            try:
                vcf_path = "./data/VCF/" + sample_filter + ".vcf.gz"
                vcf_df = vcf_to_df(vcf_path)
                st.dataframe(vcf_df)
                with open(vcf_path, "rb") as vcf:
                    st.download_button(
                        label="Download calls in VCF format",
                        data=vcf,
                        file_name=sample_filter + ".vcf.gz",
                    )
            except FileNotFoundError:
                st.warning("VCF file in not available", icon="⚠️")

    add_vertical_space(3)

    # Create six columns
    sd1, sd2, sd3, sd4, sd5, sd6 = st.columns(6, gap="small")

    # Fill columns with Sample metics
    sd1.metric(
        label="SNPs",
        value=int(dataset["no. of SNPs"]),
        help="""Number of single nucteotide polymorphisms (SNPs) 
                relative to the _M. tuberculosis_ H37Rv genome 
               (GenBank accession no. [NC_000962.3](https://www.ncbi.nlm.nih.gov/nuccore/NC_000962.3/)
            """,
    )

    sd2.metric(
        label="GC %",
        value=int(dataset["%GC"]),
        help="""GC-content (guanine-cytosine content) in the sample
            """,
    )

    sd3.metric(label="Total Sequences", value=int(dataset["Total sequences"]))

    sd4.metric(
        label="Average sequence length",
        value=float(round(dataset["Average sequence length"], 2)),
    )

    sd5.metric(
        label="Mapped Reads %",
        value=float(round(dataset["%Reads mapped"], 2)),
        help="""Percenatege of the reads mapped to the _M. tuberculosis_ H37Rv genome 
            (GenBank accession no. [NC_000962.3](https://www.ncbi.nlm.nih.gov/nuccore/NC_000962.3/)
            """,
    )

    sd6.metric(
        label="Average coverage depth",
        value=float(round(dataset["Average coverage depth"], 2)),
        help="""Mean depth of the sample mapped to the _M. tuberculosis_ H37Rv genome 
            (GenBank accession no. [NC_000962.3](https://www.ncbi.nlm.nih.gov/nuccore/NC_000962.3/)
            """,
    )

    # Create another six columns
    sd7, sd8, sd9, sd10, sd11, sd12 = st.columns(6, gap="small")

    sd7.metric(
        label="Country of Isolation", value=str(dataset["Country of isolation"].item())
    )

    sd8.metric(label="Level 1", value=str(dataset["level 1"].item()))
    sd9.metric(label="Level 2", value=str(dataset["level 2"].item()))
    sd10.metric(label="Level 3", value=str(dataset["level 3"].item()))
    sd11.metric(label="Level 4", value=str(dataset["level 4"].item()))
    sd12.metric(label="Level 5", value=str(dataset["level 5"].item()))


@st.experimental_memo
def get_chart():
    no_vars = (
        load_dataset()[["level 1", "no. of SNPs"]]
        .groupby(["level 1"])
        .mean()
        .reset_index()
        .rename(columns={"level 1": "Main lineage", "no. of SNPs": "Number of SNPs"})
    )

    no_samples = (
        load_dataset()[["level 1", "Sample"]]
        .groupby(["level 1"])
        .count()
        .reset_index()
        .rename(columns={"Sample": "Number of Samples", "level 1": "Main lineage"})
    )

    snp_chart = (
        alt.Chart(no_vars)
        .mark_bar(cornerRadiusTopLeft=3, cornerRadiusTopRight=3)
        .encode(
            x=alt.X("Main lineage", axis=alt.Axis(title="")),
            y="Number of SNPs",
            color=alt.value("#A65AA3"),
        )
    )

    sample_chart = (
        alt.Chart(no_samples)
        .mark_bar(cornerRadiusTopLeft=3, cornerRadiusTopRight=3)
        .encode(
            x=alt.X("Main lineage", axis=alt.Axis(title="")),
            y="Number of Samples",
            color=alt.value("#88AAC7"),
        )
    )

    fig_col1, fig_col2 = st.columns(2, gap="large")

    with fig_col2:
        st.markdown("### Average Number of SNPs per Lineage")
        st.altair_chart(snp_chart, theme="streamlit", use_container_width=True)

    with fig_col1:
        st.markdown("### Total Number of Samples per Lineage")
        st.altair_chart(sample_chart, theme="streamlit", use_container_width=True)


if __name__ == "__main__":
    set_page_config()
    sidebar_image()
    set_css()
    author_link()
    home_page()
    page_info()

    colored_header(
        label="Dataset",
        description="Reference Dataset",
        color_name="light-blue-70",
    )
    sample_count()
    show_dataset()
    add_vertical_space(2)

    colored_header(
        label="Statistics",
        description="Various Sample Statistics",
        color_name="blue-70",
    )
    sample_stats()
    add_vertical_space(5)

    get_chart()
    add_vertical_space(5)

    colored_header(
        label="Map Showing the Distribution of Samples",
        description="Samples without information about the country of isolation are not shown",
        color_name="violet-70",
    )
    get_map().to_streamlit(height=700)

    st.markdown(
        "\
        <a style='text-decoration: none' \
            href='#reference-dataset-of-mycobacterium-tuberculosis-complex-isolates'>\
            <span style='color: #7A3777; font-weight:bold'>&#x21E7; </span>\
            <span style='color: #A65AA3; font-weight:bold'>Back to top</span></a>\
            ",
        unsafe_allow_html=True,
    )
