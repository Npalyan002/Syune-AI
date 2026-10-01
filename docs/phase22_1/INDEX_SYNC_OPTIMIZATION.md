# Index sync optimization

Incremental synchronization reads bounded change-journal batches from the last sequence cursor. Inserts and replacements update postings, vectors, truth groups, and supersession state without scanning canonical memory. The cursor advances only through returned journal records.

Explicit rebuild resets the cursor and reconstructs derived state. This recovery path remains O(N). Locks serialize local sync and query mutations. Final authorization and temporal checks read canonical records, so a stale payload cannot grant access.
