# Retrieval routing

Exact-ID requests route to exact/entity with lexical fallback. Temporal language routes to temporal/lexical/entity with bounded associative/semantic fallback. Conceptual language routes semantic/associative with lexical fallback. Relationship language routes lexical/associative. Mixed queries use lexical/entity/associative and call semantic only when primary seeds are insufficient.

Fallback is capped at eight semantic candidates and requires a 0.70 normalized score. Weak isolated lexical/entity overlap is rejected; graph-linked weak seeds remain eligible for multi-hop.
