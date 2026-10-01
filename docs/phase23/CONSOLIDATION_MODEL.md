# Consolidation model

Exact duplicate identity is SHA-256 over entity type, fact key, context key, and whitespace/case-normalized content. The first active record stays canonical. Later exact duplicates are persisted as archived evidence, point to the canonical ID through `source_memory_ids`, and reinforce the canonical record.

This is conservative evidence consolidation: source observations and provenance remain intact. Near matches are not merged. Different fact/context keys, temporal facts, contradictions, purposes, or security envelopes therefore do not become one canonical assertion. Semantic similarity alone is never identity.
