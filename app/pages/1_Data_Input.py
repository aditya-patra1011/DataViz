"""Data Input page: type, paste, upload, or pick a sample dataset."""

import sys
from pathlib import Path

# Add the project root to the import path (only once, since Streamlit reruns this file)
ROOT = str(Path(__file__).resolve().parents[2])
if ROOT not in sys.path:
    sys.path.append(ROOT)

import streamlit as st  # noqa: E402

from core import config, ingest  # noqa: E402

st.set_page_config(
    page_title=f"Data Input · {config.APP_TITLE}", page_icon=config.APP_ICON, layout="wide"
)

st.title("📥 Data Input")
st.write("Load a dataset with one of the tabs below. It becomes the active dataset on every page.")


def set_dataset(df, source: str) -> None:
    """Store the dataset in session state so every page can use it."""
    st.session_state["df"] = df
    st.session_state["source"] = source
    st.session_state["df_original"] = df  # kept so the Clean page can undo its changes
    st.session_state["clean_log"] = []
    st.success(f"Loaded {len(df):,} rows × {len(df.columns)} columns from {source}.")


tab_type, tab_paste, tab_upload, tab_sample = st.tabs(
    ["✏️ Type", "📋 Paste", "📁 Upload", "🧪 Sample"]
)

with tab_type:
    st.caption("The first column holds labels and the others hold numbers. Use + to add rows.")
    column_text = st.text_input("Column names (comma-separated)", value="Label, Value")
    try:
        columns = ingest.parse_column_names(column_text)
    except ingest.IngestError as err:
        st.error(str(err))
    else:
        # The key changes with the columns, so the table resets when they change
        edited = st.data_editor(
            ingest.empty_table(columns), num_rows="dynamic", key=f"editor_{'|'.join(columns)}"
        )
        if st.button("Use this data", key="use_typed"):
            try:
                set_dataset(ingest.from_editor(edited), "manual entry")
            except ingest.IngestError as err:
                st.error(str(err))

with tab_paste:
    st.caption("Copy cells from Excel or Google Sheets (including the header row), or paste CSV.")
    text = st.text_area("Paste data here", height=200, placeholder="Month\tSales\nJan\t120")
    if st.button("Use this data", key="use_pasted"):
        try:
            set_dataset(ingest.parse_text(text), "pasted data")
        except ingest.IngestError as err:
            st.error(str(err))

with tab_upload:
    uploaded = st.file_uploader("Choose a CSV or Excel file", type=config.ALLOWED_FILE_TYPES)
    if uploaded is not None and st.button("Use this data", key="use_uploaded"):
        try:
            set_dataset(ingest.read_file(uploaded, uploaded.name), uploaded.name)
        except ingest.IngestError as err:
            st.error(str(err))

with tab_sample:
    samples = ingest.list_samples()
    if not samples:
        st.info("No sample datasets found in data/samples/.")
    else:
        choice = st.selectbox("Sample dataset", samples)
        if st.button("Use this data", key="use_sample"):
            set_dataset(ingest.load_sample(choice), f"sample: {choice}")

st.divider()

df = st.session_state.get("df")
if df is None:
    st.info("No dataset loaded yet.")
else:
    st.subheader(f"Active dataset ({st.session_state.get('source', 'unknown')})")
    rows_col, cols_col = st.columns(2)
    rows_col.metric("Rows", f"{len(df):,}")
    cols_col.metric("Columns", len(df.columns))
    st.dataframe(df.head(100))
    if len(df) > 100:
        st.caption(f"Showing the first 100 of {len(df):,} rows.")
