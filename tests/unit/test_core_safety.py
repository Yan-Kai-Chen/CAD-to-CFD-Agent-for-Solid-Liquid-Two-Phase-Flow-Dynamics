from fromcad2cfd_core.safety import is_private_geometry_path


def test_private_geometry_extensions() -> None:
    assert is_private_geometry_path("model.SLDPRT")
    assert is_private_geometry_path("model.step")
    assert is_private_geometry_path("mesh.stl")


def test_non_geometry_extensions() -> None:
    assert not is_private_geometry_path("README.md")
    assert not is_private_geometry_path("config.yaml")
