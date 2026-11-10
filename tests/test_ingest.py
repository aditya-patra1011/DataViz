from io import BytesIO

import pandas as pd
import pytest

from core import config, ingest


def test_get_extension_is_lowercase_without_dot():
    assert ingest.get_extension("Sales.CSV") == "csv"
    assert ingest.get_extension("report.final.xlsx") == "xlsx"


def test_clean_column_names():
    result = ingest.clean_column_names([" Sales ", "", "Unnamed: 2", "Sales"])
    assert result == ["Sales", "column_2", "column_3", "Sales_2"]


def test_read_csv_file():
    file = BytesIO(b"Month,Sales\nJan,120\nFeb,135\n")
    df = ingest.read_file(file, "sales.csv")
    assert list(df.columns) == ["Month", "Sales"]
    assert len(df) == 2


def test_read_csv_falls_back_for_non_utf8_text():
    file = BytesIO("City,Temp\nZürich,12\n".encode("latin-1"))
    df = ingest.read_file(file, "cities.csv")
    assert df.loc[0, "City"] == "Zürich"


def test_read_excel_file():
    buffer = BytesIO()
    pd.DataFrame({"A": [1, 2], "B": [3, 4]}).to_excel(buffer, index=False)
    buffer.seek(0)
    df = ingest.read_file(buffer, "numbers.xlsx")
    assert df.shape == (2, 2)


def test_unsupported_file_type_is_rejected():
    with pytest.raises(ingest.IngestError, match="Unsupported"):
        ingest.read_file(BytesIO(b"x"), "notes.txt")


def test_empty_file_is_rejected():
    with pytest.raises(ingest.IngestError):
        ingest.read_file(BytesIO(b""), "empty.csv")


def test_too_many_rows_is_rejected(monkeypatch):
    monkeypatch.setattr(config, "MAX_ROWS", 2)
    with pytest.raises(ingest.IngestError, match="limit"):
        ingest.parse_text("a\n1\n2\n3")


def test_parse_tab_separated_text():
    df = ingest.parse_text("Month\tSales\nJan\t120\nFeb\t135")
    assert list(df.columns) == ["Month", "Sales"]
    assert df["Sales"].tolist() == [120, 135]


def test_rows_wider_than_the_header_are_rejected_not_silently_cut():
    with pytest.raises(ingest.IngestError, match="more values"):
        ingest.parse_text("a,b\n1,2,3,4,5")
    with pytest.raises(ingest.IngestError, match="more values"):
        ingest.read_file(BytesIO(b"a,b\n1,2,3\n4,5,6\n"), "wide.csv")


def test_from_table_makes_numbers_and_skips_blank_rows():
    df = ingest.from_table(["Label", "Value"], [["Jan", "1,200"], ["", ""]])
    assert df["Value"].tolist() == [1200.0]


def test_from_table_rejects_text_in_number_columns():
    with pytest.raises(ingest.IngestError, match="not a number"):
        ingest.from_table(["Label", "Value"], [["Jan", "lots"]])


def test_parse_comma_separated_text():
    df = ingest.parse_text("a,b\n1,2\n")
    assert df.shape == (1, 2)


def test_parse_blank_text_is_rejected():
    with pytest.raises(ingest.IngestError, match="Nothing"):
        ingest.parse_text("   \n  ")


def test_parse_column_names():
    assert ingest.parse_column_names("Label, Value, ,Value") == ["Label", "Value", "Value_2"]


def test_parse_column_names_rejects_blank():
    with pytest.raises(ingest.IngestError):
        ingest.parse_column_names(" , ")


def test_from_editor_drops_blank_rows():
    table = ingest.empty_table(["Label", "Value"], rows=3)
    table.loc[0] = ["Jan", 120.0]
    df = ingest.from_editor(table)
    assert len(df) == 1
    assert df.loc[0, "Value"] == 120.0


def test_from_editor_with_only_blank_rows_is_rejected():
    with pytest.raises(ingest.IngestError):
        ingest.from_editor(ingest.empty_table(["Label", "Value"]))


def test_sample_datasets_load():
    samples = ingest.list_samples()
    assert samples, "expected sample CSVs in data/samples/"
    for name in samples:
        assert not ingest.load_sample(name).empty
