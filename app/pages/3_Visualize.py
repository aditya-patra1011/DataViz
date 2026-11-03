"""Visualize page: pick a chart type and columns, and get an interactive chart."""

import sys
from pathlib import Path

# Add the project root to the import path (only once, since Streamlit reruns this file)
ROOT = str(Path(__file__).resolve().parents[2])
if ROOT not in sys.path:
    sys.path.append(ROOT)

import streamlit as st  # noqa: E402

from core import charts, config, profile  # noqa: E402

NO_COLUMN = "(none)"

st.set_page_config(
    page_title=f"Visualize · {config.APP_TITLE}", page_icon=config.APP_ICON, layout="wide"
)

st.title("📈 Visualize")

df = st.session_state.get("df")
if df is None:
    st.info("No dataset loaded yet. Load one on the **Data Input** page first.")
    st.stop()

kinds = charts.column_kinds(df)
chart_name = st.selectbox("Chart type", list(charts.CHARTS))
spec = charts.CHARTS[chart_name]
st.caption(spec.description)

x_options = charts.columns_of_kind(kinds, spec.x)
y_options = charts.columns_of_kind(kinds, spec.y)
color_options = charts.columns_of_kind(kinds, (profile.CATEGORICAL,))

if (spec.x and not spec.x_optional and not x_options) or (spec.y and not y_options):
    st.warning(f"This dataset has no suitable columns for a {chart_name.lower()} chart.")
    st.stop()

# Keys include the chart name, so every chart type remembers its own choices
x = y = color = None
controls = st.columns(3)
if spec.x:
    choices = ([NO_COLUMN] if spec.x_optional else []) + x_options
    x = controls[0].selectbox("X axis", choices, key=f"{chart_name}_x")
    x = None if x == NO_COLUMN else x
if spec.y:
    # Two numeric axes (a scatter) start on two different columns
    start = 1 if x == y_options[0] and len(y_options) > 1 else 0
    y = controls[1].selectbox("Y axis", y_options, index=start, key=f"{chart_name}_y")
if spec.color and color_options:
    picked = controls[2].selectbox(
        "Colour by", [NO_COLUMN] + color_options, key=f"{chart_name}_color"
    )
    color = None if picked == NO_COLUMN else picked

agg = "sum"
if spec.aggregates and charts.has_repeats(df, x, color):
    agg = st.radio(
        "Several rows share the same X. Combine them with:",
        charts.AGGREGATIONS,
        horizontal=True,
        key=f"{chart_name}_agg",
    )

stacked = True
if spec.stacks and color:
    stacked = st.toggle("Stack bars", value=True, key=f"{chart_name}_stacked")

bins = None
if spec.bins and kinds[x] != profile.CATEGORICAL:
    bins = st.slider("Number of bins", 5, 100, 20, key=f"{chart_name}_bins")

title = st.text_input("Chart title (optional)", key=f"{chart_name}_title")

try:
    result = charts.build_chart(
        df,
        chart_name,
        x=x,
        y=y,
        color=color,
        agg=agg,
        stacked=stacked,
        bins=bins,
        title=title.strip() or None,
        dark=st.context.theme.type == "dark",
    )
except charts.ChartError as err:
    st.error(str(err))
    st.stop()

# theme=None keeps the chart's own colours instead of Streamlit's
st.plotly_chart(result.figure, theme=None, config=charts.plot_config(result))
st.caption("Hover for exact values, drag to zoom, and use the camera icon to save a PNG.")

for note in result.notes:
    st.caption(f"ℹ️ {note}")

with st.expander("Data behind this chart"):
    st.dataframe(result.data.head(1000), hide_index=True)
