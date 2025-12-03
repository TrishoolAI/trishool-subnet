from enum import Enum


class SandboxNetworkMode(str, Enum):
    # Restricted to sandbox-only local network (default)
    SANDBOX = "sandbox"

    # Full Internet access
    PUBLIC = "public"

    # Connected to both Docker internal network and Internet
    BOTH = "both"
