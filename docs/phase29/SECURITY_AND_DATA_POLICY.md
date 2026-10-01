# Security and data policy

API keys stay in process memory and are never included in evidence. Authorization, credential,
secret, cookie and session fields are removed recursively, including JSON-encoded raw bodies.
`LOCAL_ONLY`, external-disabled and provider allowlists are enforced before routing. Retrieved text
remains user/data content; adapters never elevate it to system authority. Raw evidence retention
must be shorter than normalized audit retention and governed by deployment data classification.
