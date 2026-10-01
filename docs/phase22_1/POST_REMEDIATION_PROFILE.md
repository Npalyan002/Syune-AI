# Post-remediation profile

At 100K, twenty broad queries produced 15,921 calls and 0.007 seconds cumulative, versus 7,979,741 calls and 5.098 seconds before remediation. Work is capped at 256 candidates in the V2 workload.

Status of original paths: repository snapshot REMOVED from query; sync full scan REMOVED from ordinary sync; truth comparison BOUNDED; supersession reconstruction REMOVED; health full count REMOVED; broad lexical sorting BOUNDED. Full rebuild remains O(N) in RECOVERY_TIME.

Memory is bounded per query by the candidate budget. Build/index storage remains proportional to corpus size, as expected for derived indexes.
