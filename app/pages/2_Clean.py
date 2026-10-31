"""Clean page: check data quality and fix problems one step at a time."""

import sys
from pathlib import Path

# Add the project root to the import path (only once, since Streamlit reruns this file)
ROOT = str(Path(__file__).resolve().parents[2])
if ROOT not in sys.path:
    sys.path.append(ROOT)

import streamlit as st  # noqa: E402

from core import clean, config, profile  # noqa: E402

st.set_page_config(
    page_title=f"Clean · {config.APP_TITLE}", page_icon=config.APP_ICON, layout="wide"
)

st.title("🧹 Clean")

df = st.session_state.get("df")
if df is None:
    st.info("No dataset loaded yet. Load one on the **Data Input** page first.")
    st.stop()

st.session_state.setdefault("df_original", df)
st.session_state.setdefault("clean_log", [])


def apply(step, *args) -> None:
    """Run a cleaning step on the active dataset, record it in the log, and refresh the page."""
    try:
        new_df, message = step(st.session_state["df"], *args)
    except clean.CleanError as err:
        st.error(str(err))
        return
    st.session_state["df"] = new_df
    st.session_state["clean_log"].append(message)
    st.session_state["clean_message"] = message
    st.rerun()


# Show the result of the last step (saved before the rerun)
message = st.session_state.pop("clean_message", None)
if message:
    st.success(message)

# ---- Data quality report ----
summary = profile.dataset_summary(df)
report = profile.column_report(df)

for col, (label, value) in zip(st.columns(4), summary.items(), strict=True):
    col.metric(label.capitalize(), f"{value:,}")

st.subheader("Column report")
st.dataframe(report, hide_index=True)

# ---- Fixes ----
st.subheader("Fix problems")

to_convert = report.loc[report["needs conversion"], "column"].tolist()
with st.expander(f"🔤 Convert types ({len(to_convert)} column(s))"):
    st.caption("Turns text that holds numbers or dates into real numbers and dates.")
    if to_convert:
        st.write("Will convert: " + ", ".join(to_convert))
    if st.button("Convert", disabled=not to_convert):
        apply(clean.convert_types)

with st.expander(f"🧬 Duplicate rows ({summary['duplicate rows']})"):
    st.caption("Removes rows that are exact copies of an earlier row.")
    if st.button("Remove duplicates", disabled=summary["duplicate rows"] == 0):
        apply(clean.drop_duplicates)

missing_cols = report.loc[report["missing"] > 0, "column"].tolist()
with st.expander(f"❓ Missing values ({len(missing_cols)} column(s))"):
    if not missing_cols:
        st.write("No missing values.")
    else:
        column = st.selectbox("Column", missing_cols, key="missing_column")
        strategy = st.selectbox("Fix by", clean.MISSING_STRATEGIES, key="missing_strategy")
        value = None
        if strategy == "fixed value":
            value = st.text_input("Fill value", key="missing_value")
        if st.button("Apply", key="apply_missing"):
            apply(clean.fill_missing, column, strategy, value)

outlier_cols = report.loc[report["outliers"] > 0, "column"].tolist()
with st.expander(f"📏 Outliers ({len(outlier_cols)} column(s))"):
    st.caption(
        f"Outliers are values more than {config.IQR_MULTIPLIER} × IQR below the 25th "
        "percentile or above the 75th percentile."
    )
    if not outlier_cols:
        st.write("No outliers found.")
    else:
        column = st.selectbox("Column", outlier_cols, key="outlier_column")
        low, high = profile.outlier_bounds(df[column])
        st.write(f"Normal range for '{column}': {low:.2f} to {high:.2f}")
        method = st.selectbox("Fix by", clean.OUTLIER_METHODS, key="outlier_method")
        if st.button("Apply", key="apply_outliers"):
            apply(clean.handle_outliers, column, method)

with st.expander("🗑️ Drop a column"):
    column = st.selectbox("Column", df.columns, key="drop_column")
    if st.button("Drop", key="apply_drop"):
        apply(clean.drop_column, column)

# ---- Log and reset ----
st.subheader("Cleaning log")
log = st.session_state["clean_log"]
if log:
    for number, step in enumerate(log, start=1):
        st.write(f"{number}. {step}")
else:
    st.caption("No changes yet.")

if st.button("↩️ Reset to original data", disabled=not log):
    st.session_state["df"] = st.session_state["df_original"]
    st.session_state["clean_log"] = []
    st.session_state["clean_message"] = "Restored the original data."
    st.rerun()

st.subheader("Preview")
st.dataframe(df.head(100))
