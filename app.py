#
# Created on Fri Dec 26 2025
# Copyright (c) 2025 Huy Truong
# ------------------------------
# Purpose: The main GUI
# Require: Streamlit
# ------------------------------
#
from io import BytesIO
import streamlit as st
import pandas as pd
from matplotlib.colors import to_rgb
from streamlit.runtime.uploaded_file_manager import UploadedFile
from task_assignment.core.injector import inject


def is_hex_color(s):
    try:
        to_rgb(s)
        return True
    except ValueError:
        return False


@st.cache_data
def get_and_cache_dataframe(uploaded_excel: UploadedFile) -> pd.DataFrame:
    return pd.read_excel(uploaded_excel)


st.write("# I❤️🥖- Task Assigment App")
st.write("Tutorial: Fill params -> Upload excel file -> Click the button Solve -> Download the output excel file.")
st.write("## Parameters")
num_preview_rows = st.slider("Number of preview rows", 1, 500, 100)

do_fullview = st.checkbox("Check to keep the same view as in the input file", value=True)
do_strict = st.checkbox("Check to uphold the rule that all groups should be available within a shift", value=False)
do_preview = st.checkbox("Check to preview the excel", value=True)
do_verbose = st.checkbox("Check to print more useful information", value=True)
do_styling = st.checkbox("Check to do styling in the output file", value=True)

uploaded_excel = st.file_uploader(label="Upload an excel (.xlsx) file", type="xlsx")
df: pd.DataFrame | None = None
usecols: list[str] = []
output_name: str = "output"
if uploaded_excel is not None:
    try:
        df = get_and_cache_dataframe(uploaded_excel)
        if do_preview:
            st.dataframe(df.iloc[:num_preview_rows], use_container_width=True)

        usecols = st.multiselect(
            "Select the index and filling columns",
            df.columns,
        )

    except Exception:
        st.write("Error! File is invalid! Please try again and make sure that you upload the correct file!")

starting_row = st.number_input("Fill the **starting row index** that include the header (to extract the inner table): ", min_value=0, value=7)

raw_group_ratios = st.text_input("Enter **group ratios** splitted by comma (e.g. 7,10,11): ", value="7,10,11")
group_ratios = []
if raw_group_ratios:
    try:
        group_ratios = [int(txt) for txt in raw_group_ratios.strip().split(",")]
    except Exception as e:
        st.error("Error! Invalid format! Please try again!")
        if do_verbose:
            st.write(f"Error : {e}")
        group_ratios = []

group_colors = []
if do_styling:
    raw_group_colors = st.text_input(
        "Enter **hexcolor** splitted by comma (e.g. #000000, #ff0000, #0000ff): ",
        value=None if len(group_ratios) != 3 else "#000000,#ff0000,#0000ff",
    )
    if raw_group_colors:
        try:
            group_colors = raw_group_colors.strip().split(",")
            if not all(is_hex_color(c) for c in group_colors):
                st.error("Error! Invalid hexcolor")
                raise ValueError
            if len(group_colors) != len(group_ratios):
                st.error("Error! Length mistmatch! The length of group color list must be equal to the one of group ratio list!")
                raise ValueError
        except Exception as e:
            st.error("Error! Invalid format! Please try again!")
            if do_verbose:
                st.write(f"Error : {e}")
            group_colors = []

strategy = "full" if do_fullview else "lite"
assigned_prefix = st.text_input("Fill prefix:", value="TACN")


st.write("## Status Panel")
st.write("Current Index and filling columns selected:", usecols)
st.write("Current group ratios:", group_ratios)
if do_styling:
    st.write("Corresponding group colors: ", group_colors)

is_valid: bool = (
    len(group_ratios) > 0
    and starting_row is not None
    and df is not None
    and set(usecols).issubset(df.columns)
    and (assigned_prefix is not None and assigned_prefix != "")
)

st.write("Ready to solve: ", is_valid)
if st.button("Solve", type="primary", disabled=not is_valid):
    with st.spinner("Solving task assignment..."):
        out_df, out_dict = inject(
            main_df=df,
            usecols=usecols,
            starting_row=starting_row,
            group_ratios=group_ratios,
            assigned_prefix=assigned_prefix,
            do_styling=do_styling,
            group_colors=group_colors,
            strategy=strategy,
            do_strict_cond_all_groups_are_avail_within_a_task_group=do_strict,
            debug=0,
        )
    if out_df:
        st.success("Task finished! Wait a moment and click on the button Dowload to get the output file!")
        if do_verbose:
            st.write("Debug info: ", out_dict)

        # Create a BytesIO buffer
        output = BytesIO()
        # Write Excel file to buffer
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            out_df.to_excel(writer, index=False, sheet_name="Sheet1")
            # writer.close()

        # Move buffer cursor to the beginning
        output.seek(0)

        # Create download button
        st.download_button(
            label="Download output excel",
            data=output,
            file_name=f"{output_name}.xlsx",
            # mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

    else:
        st.error("Error! Unable to solve the task given parameters!")
