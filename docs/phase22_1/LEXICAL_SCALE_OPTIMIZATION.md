# Lexical scale optimization

Posting cardinality plans rare terms before common terms. Ordered postings enable bounded iteration. Candidate generation stops at a fixed budget and top-K uses a heap instead of fully sorting large candidate populations.

Production budget is 2,048 lexical candidates; the isolated V2 benchmark uses 256. Diagnostics expose generated and ranked counts.

Phase 22 precision was mechanically 20% because one relevant record was evaluated against five returned records. V2 versions this as precision@1 for the single-answer workload; recall and precision@1 are 100%.
