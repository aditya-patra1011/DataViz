"""DataViz home page. Run with: streamlit run app/Home.py"""

import sys
from pathlib import Path

# Add the project root to the import path (only once, since Streamlit reruns this file)
ROOT = str(Path(__file__).resolve().parents[1])
if ROOT not in sys.path:
    sys.path.append(ROOT)

import streamlit as st  # noqa: E402

from core import config  # noqa: E402

st.set_page_config(page_title=config.APP_TITLE, page_icon=config.APP_ICON, layout="wide")

st.title(f"{config.APP_ICON} {config.APP_TITLE}")
st.write("Enter or upload data and turn it into interactive charts and insights.")

st.subheader("How it works")
st.markdown(
    """
1. **Data Input** - type your data, paste it, or upload a CSV/Excel file
2. **Clean** - fix missing values and wrong types
3. **Visualize** - pick a chart (or take the suggestion) and explore
4. **Saved** - keep datasets to come back to later
"""
)

# Shared state: the dataset every page works on
if "df" not in st.session_state:
    st.session_state["df"] = None

if st.session_state["df"] is None:
    st.info("No data loaded yet. Open **Data Input** in the sidebar to get started.")
else:
    st.success(f"Dataset loaded: {len(st.session_state['df'])} rows")
