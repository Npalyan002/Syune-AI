# Real semantic evaluation

`benchmarks/semantic_phase22.v1.json` contains human-authored labels for paraphrase, synonyms, conceptual equivalence, indirect descriptions, terminology variation, entity description, and hard negatives. Labels are independent of embedding code.

Real embedding execution: `NOT_EXECUTED`. Therefore LEXICAL, ASSOCIATIVE, SEMANTIC, LEXICAL+SEMANTIC, SEMANTIC+ASSOCIATIVE, and FULL ROUTED HYBRID quality results are `NOT_EXECUTED`; deterministic hash embeddings are not presented as real evidence.

Router-only analysis invoked 3.0 primary retrievers/query versus 6.0 for run-all, a 50% fanout reduction. Fallback rate, useful-candidate count, and real-semantic quality remain unvalidated.
