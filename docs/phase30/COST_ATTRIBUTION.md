# Cost attribution

Every APPLIED cognitive transaction records gateway cost and a subsystem label. Aggregation is
available through `cost_by_subsystem()`. Canonical labels are `learning`, `organizational_learning`,
`planning`, `cognition`, `verification`, and `other`; the generic service accepts the concrete label
because current P0 cognitive modules remain deterministic. Failed/unapplied operations are excluded
from applied cognitive cost while gateway attempt telemetry remains available separately.
