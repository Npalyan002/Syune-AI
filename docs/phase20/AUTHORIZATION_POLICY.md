# Authorization policy

Decisions are deterministic `ALLOW_*` or `DENY_*` codes. Evaluation order is: public exception, valid principal, explicit deny, purpose, organization/project/department/agent scopes, owner, explicit allow, owner mismatch, restricted sensitivity, matching shared scope, default deny.

Explicit deny always wins over allow. Missing identity fails closed for secured non-public resources. Restricted resources require ownership or explicit principal access. Purpose constraints require an exact declared purpose.

Decision details are retained in internal access audit events but denied retrieval results expose neither resource metadata nor policy details.
