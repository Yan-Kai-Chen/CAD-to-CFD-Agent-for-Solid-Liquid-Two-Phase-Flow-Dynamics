from fromcad2cfd_solidworks.import_cleanup import infer_sphere_from_box, semicircle_polyline_points


def test_semicircle_polyline_points_include_axis_endpoints():
    points = semicircle_polyline_points(20.0, 8)

    assert len(points) == 9
    assert points[0] == (0.0, -20.0)
    assert points[-1] == (0.0, 20.0)
    assert max(x for x, _ in points) == 20.0


def test_infer_sphere_from_box_returns_center_radius_and_roundness():
    inferred = infer_sphere_from_box([-0.02, -0.02, -0.02, 0.02, 0.02, 0.02])

    assert inferred["center_mm"] == [0.0, 0.0, 0.0]
    assert abs(inferred["radius_mm"] - 20.0) < 1e-9
    assert inferred["roundness_error_pct"] == 0.0

