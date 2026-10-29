from core import config


def test_paths_point_inside_project():
    assert config.DATA_DIR.parent == config.ROOT_DIR
    assert config.DB_PATH.parent == config.DATA_DIR


def test_allowed_file_types_are_plain_lowercase_extensions():
    for ext in config.ALLOWED_FILE_TYPES:
        assert ext == ext.lower()
        assert not ext.startswith(".")
