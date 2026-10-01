# Budget policy

Every attempt—including retry, repair and fallback—must reserve call count, estimated input,
maximum output and estimated cost before transport. Request, task, agent, project, organization and
experiment scopes use the same atomic hierarchy. Measured usage reconciles reservations; unknown
usage remains conservatively charged. Any parent denial wins over recovery.
