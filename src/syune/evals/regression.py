"""Coarse local regression flags, not cross-platform service-level promises."""
def compare(baseline, current, platform):
    if baseline.platform != platform:
        return ("platform differs: establish a comparable baseline",)
    values = {m.name: m.value for m in current}
    issues = []
    for metric in baseline.metrics:
        value = values.get(metric.name)
        if value is None:
            issues.append(metric.name + ": missing")
        elif metric.name == "test_count":
            if value < metric.value: issues.append("test_count: coverage decreased")
        elif metric.name == "error_count":
            if value > metric.value: issues.append("error_count: regression")
        elif value > metric.value + max(baseline.absolute_tolerance, abs(metric.value)*baseline.relative_tolerance):
            issues.append(metric.name + ": regression")
    return tuple(issues)
