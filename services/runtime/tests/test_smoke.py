import cadre


def test_package_importable():
    assert cadre is not None


def test_version_is_string():
    assert isinstance(cadre.__version__, str)
    assert cadre.__version__
