from datetime import datetime, timezone
from uuid import UUID

import pytest

from syune.core import ClaimId, Confidence, ConceptId, ProvenanceId, SourceId
from syune.memory import Provenance


@pytest.fixture
def now():
    return datetime(2026, 1, 1, tzinfo=timezone.utc)


@pytest.fixture
def ids():
    return {
        "source": SourceId(UUID(int=1)),
        "concept": ConceptId(UUID(int=2)),
        "claim": ClaimId(UUID(int=3)),
        "provenance": ProvenanceId(UUID(int=4)),
    }


@pytest.fixture
def provenance(now, ids):
    return Provenance(ids["provenance"], ids["source"], now)


@pytest.fixture
def confidence():
    return Confidence(0.6)
