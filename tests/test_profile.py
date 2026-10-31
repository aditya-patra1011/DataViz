import pandas as pd

from core import profile


def test_to_number_strips_separators_and_symbols():
    result = profile.to_number(pd.Series(["1,200", "$5", "7%", "abc", None]))
    assert result.tolist()[:3] == [1200.0, 5.0, 7.0]
    assert result.iloc[3:].isna().all()


def test_detect_numeric_column():
    assert profile.detect_type(pd.Series([1, 2, 3])) == profile.NUMERIC


def test_detect_numbers_stored_as_text():
    assert profile.detect_type(pd.Series(["1,000", "2,500", "300"])) == profile.NUMERIC


def test_detect_dates_stored_as_text():
    assert profile.detect_type(pd.Series(["2025-01", "2025-02", "2025-03"])) == profile.DATETIME


def test_month_names_are_not_dates():
    assert profile.detect_type(pd.Series(["Jan", "Feb", "Mar"])) == profile.CATEGORICAL


def test_detect_categorical_column():
    assert profile.detect_type(pd.Series(["A", "B", "A", "B"])) == profile.CATEGORICAL


def test_detect_text_column():
    values = pd.Series([f"comment number {i}" for i in range(30)])
    assert profile.detect_type(values) == profile.TEXT


def test_empty_column_is_text():
    assert profile.detect_type(pd.Series([None, None])) == profile.TEXT


def test_needs_conversion():
    assert profile.needs_conversion(pd.Series(["1", "2"]), profile.NUMERIC)
    assert not profile.needs_conversion(pd.Series([1, 2]), profile.NUMERIC)


def test_outlier_mask_finds_extreme_value():
    series = pd.Series([10, 11, 12, 13, 12, 11, 100])
    assert profile.outlier_mask(series).tolist() == [False] * 6 + [True]


def test_column_report():
    df = pd.DataFrame({"name": ["a", "b", None], "score": [1.0, 2.0, 3.0]})
    report = profile.column_report(df).set_index("column")
    assert report.loc["name", "missing"] == 1
    assert report.loc["score", "type"] == profile.NUMERIC
    assert report.loc["score", "outliers"] == 0


def test_dataset_summary_counts_duplicates_and_missing():
    df = pd.DataFrame({"a": [1, 1, None], "b": ["x", "x", "y"]})
    summary = profile.dataset_summary(df)
    assert summary == {"rows": 3, "columns": 2, "missing cells": 1, "duplicate rows": 1}
