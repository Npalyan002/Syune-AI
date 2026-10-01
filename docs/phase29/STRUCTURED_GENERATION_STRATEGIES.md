# Structured generation strategies

The gateway supports plain JSON prompting, native JSON schema, compact schema, explicit repair,
and caller-orchestrated two-stage generation. The live v1 matrix used all seven major roles and
small/medium/large synthetic schemas. Each strategy committed 7/7. Two-stage cost $0.018363 and
had 5.02 s median latency, versus roughly $0.0058–$0.0066 and 1.35–2.04 s for direct strategies.
Compact schema did not reduce tokens in this sample. These small samples characterize behavior;
they do not establish narrow statistical superiority.
