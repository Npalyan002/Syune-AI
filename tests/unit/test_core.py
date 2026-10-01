from datetime import datetime, timedelta, timezone
from uuid import UUID

import pytest

from syune.core import ClaimId, Confidence, ConceptId, SourceId, require_utc, utc_now


def test_ids_are_typed_stable_and_injectable():
    value = UUID(int=42)
    source = SourceId.new(lambda: value)
    assert source == SourceId.parse(str(value))
    assert str(source) == str(value)
    assert source != ConceptId(value)
    assert hash(source) == hash(SourceId(value))


def test_ids_reject_non_uuid():
    with pytest.raises(TypeError):
        SourceId("file.txt")


def test_utc_clock_and_validation():
    now = utc_now()
    require_utc(now)
    assert now.utcoffset() == timedelta(0)
    with pytest.raises(ValueError):
        require_utc(datetime(2026, 1, 1))
    with pytest.raises(ValueError):
        require_utc(datetime(2026, 1, 1, tzinfo=timezone(timedelta(hours=1))))


@pytest.mark.parametrize("value", [-0.1, 1.1, float("nan"), float("inf")])
def test_confidence_rejects_invalid_range(value):
    with pytest.raises(ValueError):
        Confidence(value)


def test_confidence_value_semantics():
    assert Confidence(0.5) == Confidence(0.5)
    assert Confidence(0.0).value == 0
    assert Confidence(1.0).value == 1
    with pytest.raises(TypeError):
        Confidence(True)
