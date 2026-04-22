import keel_runtime


def test_package_importable():
    assert keel_runtime is not None


def test_version_is_string():
    assert isinstance(keel_runtime.__version__, str)
    assert keel_runtime.__version__
