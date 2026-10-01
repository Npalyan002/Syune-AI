# Retrieval failure tests

Automated tests cover embedding outage with lexical continuity, provider batch/dimension validation, Qdrant upsert/search/delete/health, restart embedding-space mismatch, canonical rebuild equivalence, future strongest-match rejection, and semantic denial across agent, project, organization, and purpose boundaries.

Live network outage and corrupt Qdrant storage recovery were not executed. Corrupt or mismatched derived metadata maps to explicit failure and rebuild; canonical memory is never mutated.
