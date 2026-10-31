import pandas as pd
import pytest

from core import clean


@pytest.fixture
def scores():
    return pd.DataFrame(
        {
            "name": ["Ana", "Ben", "Cy", "Di", "Ed", "Flo", "Gus"],
            "score": [70.0, 72.0, None, 75.0, 71.0, 73.0, 300.0],
        }
    )


def test_convert_types_turns_text_into_numbers_and_dates():
    df = pd.DataFrame({"when": ["2025-01", "2025-02"], "amount": ["1,200", "$30"]})
    result, message = clean.convert_types(df)
    assert pd.api.types.is_datetime64_any_dtype(result["when"])
    assert result["amount"].tolist() == [1200.0, 30.0]
    assert "amount" in message


def test_convert_types_reports_unreadable_values():
    df = pd.DataFrame({"amount": ["1", "2", "3", "4", "oops"]})
    result, message = clean.convert_types(df)
    assert result["amount"].isna().sum() == 1
    assert "1 unreadable" in message


def test_convert_types_with_nothing_to_do_raises():
    with pytest.raises(clean.CleanError):
        clean.convert_types(pd.DataFrame({"a": [1, 2]}))


def test_input_dataframe_is_not_modified(scores):
    original = scores.copy()
    clean.fill_missing(scores, "score", "mean")
    pd.testing.assert_frame_equal(scores, original)


def test_drop_duplicates():
    df = pd.DataFrame({"a": [1, 1, 2]})
    result, message = clean.drop_duplicates(df)
    assert len(result) == 2
    assert "1 duplicate" in message


def test_drop_duplicates_with_none_raises():
    with pytest.raises(clean.CleanError):
        clean.drop_duplicates(pd.DataFrame({"a": [1, 2]}))


def test_fill_missing_drop_rows(scores):
    result, _ = clean.fill_missing(scores, "score", "drop rows")
    assert len(result) == 6


@pytest.mark.parametrize(
    ("strategy", "expected"),
    [("mean", 110.17), ("median", 72.5), ("most common", 70.0)],
)
def test_fill_missing_with_statistic(scores, strategy, expected):
    result, _ = clean.fill_missing(scores, "score", strategy)
    assert result.loc[2, "score"] == expected


def test_fill_missing_fixed_value_on_numeric_column(scores):
    result, _ = clean.fill_missing(scores, "score", "fixed value", "0")
    assert result.loc[2, "score"] == 0.0


def test_fill_missing_fixed_value_must_be_number_for_numeric_column(scores):
    with pytest.raises(clean.CleanError, match="must be a number"):
        clean.fill_missing(scores, "score", "fixed value", "abc")


def test_mean_of_text_column_raises():
    df = pd.DataFrame({"city": ["Pune", None]})
    with pytest.raises(clean.CleanError, match="not numeric"):
        clean.fill_missing(df, "city", "mean")


def test_fill_missing_on_complete_column_raises(scores):
    with pytest.raises(clean.CleanError, match="no missing"):
        clean.fill_missing(scores, "name", "most common")


def test_remove_outlier_rows(scores):
    result, _ = clean.handle_outliers(scores, "score", "remove rows")
    assert 300.0 not in result["score"].tolist()
    assert len(result) == 6


def test_cap_outliers(scores):
    result, _ = clean.handle_outliers(scores, "score", "cap at limits")
    assert len(result) == 7
    assert result["score"].max() < 300.0


def test_drop_column(scores):
    result, _ = clean.drop_column(scores, "name")
    assert list(result.columns) == ["score"]


def test_unknown_column_raises(scores):
    with pytest.raises(clean.CleanError, match="does not exist"):
        clean.drop_column(scores, "age")
