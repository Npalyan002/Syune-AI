# Decay and reinforcement

Priority is deterministic:

`priority = min(1, max(historical_importance, 0.5^(age_days / half_life_days) + min(1, reinforcement_count * 0.1)))`

The anchor is the last evidence-backed reinforcement or creation time. Decay affects lifecycle eligibility only and never mutates truth. Access increments `access_count`; it does not increment `reinforcement_count`. Reinforcement requires an explicit reason such as confirmation or independent duplicate evidence.
