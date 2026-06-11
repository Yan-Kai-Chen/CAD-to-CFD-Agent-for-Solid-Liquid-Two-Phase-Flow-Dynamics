from fromcad2cfd_core.units import m_to_mm, mm_to_m


def test_mm_to_m() -> None:
    assert mm_to_m(1000) == 1.0


def test_m_to_mm() -> None:
    assert m_to_mm(1.2) == 1200.0
