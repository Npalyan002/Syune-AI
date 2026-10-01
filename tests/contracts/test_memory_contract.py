from uuid import UUID

from syune.core import ClaimId, ConceptId, Confidence, SourceId
from syune.memory import Claim, Concept, InMemoryReferenceRepository


def test_shared_repository_preserves_type_and_provenance(now, ids, provenance):
    repo = InMemoryReferenceRepository()
    repo.put(Concept(ids["concept"], "cross-context", provenance, Confidence(0.4), now))
    repo.put(Claim(ids["claim"], "Disagreement is possible", provenance, Confidence(0.7), now))
    assert isinstance(repo.get(ids["concept"]), Concept)
    assert isinstance(repo.get(ids["claim"]), Claim)
    assert repo.get(ids["concept"]).provenance.source_id == ids["source"]
    assert SourceId(UUID(int=2)) != ids["concept"]
    assert ClaimId(UUID(int=2)) != ids["concept"]
