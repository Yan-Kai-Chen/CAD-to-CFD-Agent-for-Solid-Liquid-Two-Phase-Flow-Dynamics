from fromcad2cfd_solidworks.cfd_templates import available_templates, build_cfd_template_plan, parse_param_overrides
from fromcad2cfd_solidworks.plan_executor import PLAN_SCHEMA_VERSION, validate_plan


def test_all_cfd_templates_validate_as_phase5_plans():
    for template in available_templates():
        plan = build_cfd_template_plan(template, project="phase7_unit_test", model_name=f"unit_{template}")
        normalized = validate_plan(plan)
        assert normalized["schema_version"] == PLAN_SCHEMA_VERSION
        assert normalized["operations"]


def test_parse_param_overrides_numeric_and_bool_values():
    params = parse_param_overrides(["domain_length_mm=120", "scale=1.25", "enabled=true", "label=test"])

    assert params["domain_length_mm"] == 120
    assert params["scale"] == 1.25
    assert params["enabled"] is True
    assert params["label"] == "test"

