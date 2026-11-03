import pandas as pd
import pytest

from core import charts, config, ingest


@pytest.fixture
def sales():
    return pd.DataFrame(
        {
            "month": ["2025-02", "2025-01", "2025-02", "2025-01"],
            "region": ["North", "North", "South", "South"],
            "sales": [20.0, 10.0, 40.0, 30.0],
        }
    )


def test_every_chart_has_a_builder():
    assert set(charts.CHARTS) == set(charts.BUILDERS)


def test_columns_of_kind_filters_by_detected_type(sales):
    kinds = charts.column_kinds(sales)
    assert charts.columns_of_kind(kinds, ("numeric",)) == ["sales"]
    assert charts.columns_of_kind(kinds, ("categorical",)) == ["region"]


def test_has_repeats(sales):
    assert charts.has_repeats(sales, "month")
    assert not charts.has_repeats(sales, "month", "region")


@pytest.mark.parametrize(("agg", "expected"), [("sum", 30.0), ("mean", 15.0), ("count", 2)])
def test_bar_combines_repeated_rows(sales, agg, expected):
    result = charts.build_chart(sales, "Bar", x="region", y="sales", agg=agg)
    north = result.data.set_index("region").loc["North"]
    assert north.iloc[-1] == expected


def test_bar_sums_each_group(sales):
    result = charts.build_chart(sales, "Bar", x="region", y="sales")
    assert result.data.set_index("region")["Sum of sales"].to_dict() == {
        "North": 30.0,
        "South": 70.0,
    }


def test_rows_without_repeats_keep_their_column_name(sales):
    result = charts.build_chart(sales, "Bar", x="month", y="sales", color="region")
    assert "sales" in result.data.columns


def test_mean_bars_are_not_stacked(sales):
    result = charts.build_chart(sales, "Bar", x="month", y="sales", color="region", agg="mean")
    assert result.figure.layout.barmode == "group"


def test_sum_bars_stack_by_default(sales):
    result = charts.build_chart(sales, "Bar", x="month", y="sales", color="region")
    assert result.figure.layout.barmode == "relative"


def test_line_converts_text_dates_and_sorts_them(sales):
    result = charts.build_chart(sales, "Line", x="month", y="sales")
    months = result.data["month"]
    assert pd.api.types.is_datetime64_any_dtype(months)
    assert months.is_monotonic_increasing


def test_labels_keep_the_order_they_have_in_the_data():
    df = pd.DataFrame({"month": ["Mar", "Jan", "Feb"], "sales": [1, 2, 3]})
    result = charts.build_chart(df, "Line", x="month", y="sales")
    assert result.data["month"].tolist() == ["Mar", "Jan", "Feb"]


def test_numbers_stored_as_text_can_be_plotted():
    df = pd.DataFrame({"city": ["A", "B"], "sales": ["1,000", "2,000"]})
    result = charts.build_chart(df, "Bar", x="city", y="sales")
    assert result.data["sales"].tolist() == [1000.0, 2000.0]


def test_rows_with_missing_values_are_left_out_and_reported():
    df = pd.DataFrame({"city": ["A", "B", None], "sales": [1.0, None, 3.0]})
    result = charts.build_chart(df, "Bar", x="city", y="sales")
    assert len(result.data) == 1
    assert any("2 row(s)" in note for note in result.notes)


def test_no_usable_rows_raises():
    df = pd.DataFrame({"city": ["A", "B"], "sales": [None, None]})
    with pytest.raises(charts.ChartError, match="No rows"):
        charts.build_chart(df, "Bar", x="city", y="sales")


def test_same_column_for_x_and_y_raises(sales):
    with pytest.raises(charts.ChartError, match="different columns"):
        charts.build_chart(sales, "Scatter", x="sales", y="sales")


def test_group_colours_follow_the_name_not_the_rank():
    theme = config.CHART_THEMES["light"]
    small = charts._color_map(["South", "North"], theme)
    large = charts._color_map(["North", "South", "Other"], theme)
    assert small["North"] == large["North"] == theme["series"][0]
    assert large["Other"] == theme["muted"]


def test_extra_series_fold_into_other():
    names = [f"group {i:02d}" for i in range(12)]
    df = pd.DataFrame({"x": ["a"] * 12, "group": names, "y": range(1, 13)})
    result = charts.build_chart(df, "Bar", x="x", y="y", color="group")
    groups = set(result.data["group"])
    assert len(groups) == config.MAX_SERIES
    assert charts.OTHER in groups
    assert "group 11" in groups
    assert any(charts.OTHER in note for note in result.notes)


def test_pie_folds_small_slices_and_keeps_the_total():
    df = pd.DataFrame({"part": list("abcdefgh"), "value": [10, 9, 8, 7, 6, 5, 4, 3]})
    result = charts.build_chart(df, "Pie", x="part", y="value")
    assert len(result.data) == config.PIE_MAX_SLICES
    assert result.data.iloc[:, -1].sum() == df["value"].sum()
    assert result.data.iloc[-1, 0] == charts.OTHER


def test_pie_rejects_negative_values():
    df = pd.DataFrame({"part": ["a", "b"], "value": [5, -1]})
    with pytest.raises(charts.ChartError, match="negative"):
        charts.build_chart(df, "Pie", x="part", y="value")


def test_pie_needs_two_parts():
    df = pd.DataFrame({"part": ["a", "a"], "value": [5, 1]})
    with pytest.raises(charts.ChartError, match="two parts"):
        charts.build_chart(df, "Pie", x="part", y="value")


def test_scatter_with_few_groups_uses_colour(sales):
    df = sales.assign(cost=[1.0, 2.0, 3.0, 4.0])
    figure = charts.build_chart(df, "Scatter", x="cost", y="sales", color="region").figure
    assert {trace.name for trace in figure.data} == {"North", "South"}


def test_scatter_with_many_groups_gets_one_panel_each():
    df = pd.DataFrame({"a": range(8), "b": range(8), "group": ["p", "q", "r", "s"] * 2})
    result = charts.build_chart(df, "Scatter", x="a", y="b", color="group")
    assert len(result.figure.data) == 4
    panels = {annotation.text for annotation in result.figure.layout.annotations}
    assert panels == {"p", "q", "r", "s"}


def test_heatmap_calculates_correlations():
    df = pd.DataFrame({"a": [1, 2, 3], "b": [2, 4, 6], "c": [3, 2, 1], "name": list("xyz")})
    data = charts.build_chart(df, "Correlation heatmap").data.set_index("column")
    assert data.loc["a", "b"] == 1.0
    assert data.loc["a", "c"] == -1.0
    assert "name" not in data.columns


def test_heatmap_leaves_out_constant_columns():
    df = pd.DataFrame({"a": [1, 2, 3], "b": [3, 5, 4], "same": [7, 7, 7]})
    result = charts.build_chart(df, "Correlation heatmap")
    assert "same" not in result.data.columns
    assert any("same" in note for note in result.notes)


def test_heatmap_needs_two_numeric_columns():
    with pytest.raises(charts.ChartError, match="two numeric"):
        charts.build_chart(pd.DataFrame({"a": [1, 2]}), "Correlation heatmap")


def test_input_dataframe_is_not_modified(sales):
    original = sales.copy()
    charts.build_chart(sales, "Line", x="month", y="sales", color="region")
    pd.testing.assert_frame_equal(sales, original)


def test_dark_mode_uses_the_dark_theme(sales):
    figure = charts.build_chart(sales, "Bar", x="region", y="sales", dark=True).figure
    assert figure.layout.paper_bgcolor == config.CHART_THEMES["dark"]["surface"]


def test_custom_title_and_png_filename(sales):
    result = charts.build_chart(sales, "Bar", x="region", y="sales", title="Q1 Sales!")
    assert result.figure.layout.title.text == "Q1 Sales!"
    assert charts.plot_config(result)["toImageButtonOptions"]["filename"] == "q1-sales"


@pytest.mark.parametrize("sample", ["sales.csv", "students.csv", "weather.csv"])
@pytest.mark.parametrize("chart", list(charts.CHARTS))
def test_every_chart_draws_from_every_sample(sample, chart):
    df = ingest.load_sample(sample)
    kinds = charts.column_kinds(df)
    spec = charts.CHARTS[chart]
    x_options = charts.columns_of_kind(kinds, spec.x)
    y_options = charts.columns_of_kind(kinds, spec.y)
    x = x_options[0] if x_options else None
    y = next((column for column in y_options if column != x), None)
    colors = charts.columns_of_kind(kinds, ("categorical",))
    color = colors[-1] if spec.color and colors else None
    assert charts.build_chart(df, chart, x=x, y=y, color=color).figure.data
