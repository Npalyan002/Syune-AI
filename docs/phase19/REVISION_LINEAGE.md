# Revision lineage

`revision_of` identifies the logical predecessor and `supersedes` identifies one or more records displaced by a revision. Reverse `superseded_by` is derived by scanning `supersedes`, avoiding mutable back-pointer rewrites.

Records are immutable and never overwritten. Current retrieval suppresses both explicitly `SUPERSEDED` records and targets of a later `supersedes` edge. Historical retrieval can return a predecessor when its validity interval covers the requested time.
