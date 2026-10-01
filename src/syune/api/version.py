"""Version negotiation for the stable public contract."""

PUBLIC_API_VERSION = "1"
SUPPORTED_PUBLIC_API_VERSIONS = (PUBLIC_API_VERSION,)
MCP_CONTRACT_VERSION = "1"


def negotiate_version(host_supported: tuple[str, ...] | list[str]) -> str:
    from .errors import ErrorCategory, SyuneError

    if not isinstance(host_supported, (tuple, list)) or any(
        not isinstance(item, str) or not item.strip() for item in host_supported
    ):
        raise SyuneError("UNSUPPORTED_VERSION", "supported versions must be nonempty strings",
                         ErrorCategory.UNSUPPORTED_VERSION)
    for version in SUPPORTED_PUBLIC_API_VERSIONS:
        if version in host_supported:
            return version
    raise SyuneError("UNSUPPORTED_VERSION", "no shared public API version",
                     ErrorCategory.UNSUPPORTED_VERSION,
                     details={"host_supported": list(host_supported),
                              "syune_supported": list(SUPPORTED_PUBLIC_API_VERSIONS)})
