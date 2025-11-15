import pytest

yaml = pytest.importorskip("yaml", reason="PyYAML отсутствует в оффлайн-песочнице")


def test_yaml_import() -> None:
    assert yaml is not None
