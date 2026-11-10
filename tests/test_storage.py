import pandas as pd
import pytest

from core import storage


@pytest.fixture
def db(tmp_path):
    return tmp_path / "datasets.db"


@pytest.fixture
def df():
    return pd.DataFrame({"name": ["a", "b"], "value": [1.5, None]})


def test_save_and_load_keep_the_data(db, df):
    storage.save(db, "mine", df, "typed data")
    loaded, source = storage.load(db, "mine")
    pd.testing.assert_frame_equal(loaded, df, check_dtype=False)
    assert source == "typed data"


def test_dates_stay_dates(db):
    dates = pd.DataFrame({"when": pd.to_datetime(["2025-01-01", "2025-02-01"]), "v": [1, 2]})
    storage.save(db, "dated", dates, "file")
    loaded, _ = storage.load(db, "dated")
    assert loaded["when"].dtype.kind == "M"


def test_list_saved_is_sorted_and_has_sizes(db, df):
    storage.save(db, "zebra", df, "x")
    storage.save(db, "apple", df, "x")
    saved = storage.list_saved(db)
    assert [item["name"] for item in saved] == ["apple", "zebra"]
    assert (saved[0]["rows"], saved[0]["columns"]) == (2, 2)


def test_saving_again_replaces_and_says_so(db, df):
    assert storage.save(db, "mine", df, "x") is False
    assert storage.save(db, "mine", df.head(1), "x") is True
    assert storage.list_saved(db)[0]["rows"] == 1


def test_blank_name_is_rejected(db, df):
    with pytest.raises(storage.StorageError, match="name"):
        storage.save(db, "   ", df, "x")


def test_delete(db, df):
    storage.save(db, "mine", df, "x")
    storage.delete(db, "mine")
    assert storage.list_saved(db) == []


@pytest.mark.parametrize("action", [storage.load, storage.delete])
def test_unknown_name_is_a_friendly_error(db, action):
    with pytest.raises(storage.StorageError, match="no saved dataset"):
        action(db, "ghost")
