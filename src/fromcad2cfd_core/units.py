"""Small unit conversion helpers used by workflow layers."""

MM_TO_M = 0.001
M_TO_MM = 1000.0


def mm_to_m(value_mm: float) -> float:
    return float(value_mm) * MM_TO_M


def m_to_mm(value_m: float) -> float:
    return float(value_m) * M_TO_MM
