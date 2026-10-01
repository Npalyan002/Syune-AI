# Security envelope

`SecurityEnvelope` schema v1 carries owner, organization/project/department/agent scopes, allowed and denied principals, sensitivity, purpose constraints, and default policy.

Sensitivity levels are PUBLIC, INTERNAL, CONFIDENTIAL, and RESTRICTED. The envelope is shared by all durable memory types and persists through the existing JSON repository. Authorized memory access does not grant visibility into unauthorized association endpoints; SDK and MCP association responses filter neighbors independently.
