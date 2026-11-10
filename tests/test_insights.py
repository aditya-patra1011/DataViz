import pandas as pd
import pytest

from core import charts, ingest, recommend, stats


@pytest.fixture
def sales():
    return ingest.load_sample("sales.csv")


def test_summary_table_describes_numeric_columns():
    df = pd.DataFrame({"name": ["a", "b", "c"], "score": [1.0, 2.0, 3.0]})
    table = stats.summary_table(df).set_index("column")
    assert list(table.index) == ["score"]
    assert table.loc["score", "mean"] == 2.0
    assert table.loc["score", "max"] == 3.0


def test_summary_table_without_numbers_is_empty():
    assert stats.summary_table(pd.DataFrame({"name": ["a", "b"]})).empty


def test_strongest_pair_finds_the_closest_columns():
    df = pd.DataFrame(
        {"a": [1, 2, 3, 4, 5], "b": [2, 4, 6, 8, 10], "c": [5, 1, 4, 2, 3]}
    )
    first, second, value = stats.strongest_pair(df)
    assert (first, second) == ("a", "b")
    assert value == pytest.approx(1.0)


def test_too_few_rows_give_no_correlation():
    df = pd.DataFrame({"a": [1, 2, 3], "b": [2, 4, 6]})
    assert stats.strongest_pair(df) is None


def test_insights_report_trend_and_groups(sales):
    text = " ".join(stats.insights(sales))
    assert "Average Sales rose" in text
    assert "Jan 2025 to Dec 2025" in text
    assert "East has the highest average Sales" in text


def test_one_unusual_day_does_not_decide_the_trend():
    values = [10.0, 10.0, 10.0, 10.0, 10.0, 10.0, 10.0, 1.0]
    df = pd.DataFrame({"when": pd.date_range("2025-06-01", periods=8), "value": values})
    assert "fell 45%" in stats.insights(df)[0]


def test_correlation_insight_warns_it_is_not_causation(sales):
    assert any("doesn't prove" in finding for finding in stats.insights(sales))


def test_a_falling_trend_says_fell():
    df = pd.DataFrame({"when": ["2025-01", "2025-02", "2025-03"], "value": [30.0, 20.0, 15.0]})
    assert stats.insights(df)[0].startswith("Average value fell 50%")


def test_insights_mention_data_problems():
    text = " ".join(stats.insights(ingest.load_sample("students.csv")))
    assert "missing" in text


def test_dataset_without_patterns_says_so():
    df = pd.DataFrame({"name": ["a", "b", "c"]})
    assert stats.insights(df) == ["No clear patterns stood out in this dataset."]


def test_time_data_suggests_a_line_chart_first(sales):
    first = recommend.suggest(sales)[0]
    assert (first.chart, first.x, first.y, first.color) == ("Line", "Month", "Sales", "Region")


def test_groups_without_dates_suggest_a_bar_chart_first():
    first = recommend.suggest(ingest.load_sample("students.csv"))[0]
    assert (first.chart, first.x) == ("Bar", "Section")


def test_only_text_gives_no_suggestions():
    assert recommend.suggest(pd.DataFrame({"name": ["a", "b", "c"]})) == []


def test_weakly_related_columns_do_not_suggest_a_scatter():
    df = pd.DataFrame({"a": [1, 2, 3, 4, 5, 6], "b": [3, 1, 4, 1, 5, 2]})
    assert "Scatter" not in [item.chart for item in recommend.suggest(df)]


def test_negative_values_never_suggest_a_pie():
    df = pd.DataFrame({"group": ["a", "b"] * 5, "value": [-1, 2] * 5})
    assert "Pie" not in [item.chart for item in recommend.suggest(df)]


@pytest.mark.parametrize("sample", ["sales.csv", "students.csv", "weather.csv"])
def test_every_suggestion_can_actually_be_drawn(sample):
    df = ingest.load_sample(sample)
    suggestions = recommend.suggest(df)
    assert suggestions
    for item in suggestions:
        assert charts.build_chart(
            df, item.chart, x=item.x, y=item.y, color=item.color, agg=item.agg
        ).figure.data
