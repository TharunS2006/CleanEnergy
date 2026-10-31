"""Data model of a virtualized data centre design."""
from dataclasses import dataclass, field, replace
from typing import Dict, List, Tuple

ZONES = ["internet", "dmz", "app", "db", "mgmt", "storage"]
CRITICAL_ZONES = ["db", "mgmt", "storage"]
TIER_ZONE = {"web": "dmz", "app": "app", "db": "db", "mgmt": "mgmt"}


@dataclass
class Host:
    name: str
    cpu: int
    ram: int                       # GB
    rack: str
    feeds: Tuple[str, ...]         # power feeds (A, B ...) that can supply the host
    switches: Tuple[str, ...]      # top-of-rack switches the host is cabled to
    cooling: Tuple[str, ...]       # cooling units that keep the host's row within temperature


@dataclass
class VM:
    name: str
    cpu: int
    ram: int
    tier: str                      # web, app, db or mgmt
    group: str                     # replicas of one service: they must not share a host
    critical: bool = False

    @property
    def zone(self):
        return TIER_ZONE[self.tier]


@dataclass
class Rule:
    src: str
    dst: str
    port: str                      # a port number as text, or "any"
    action: str                    # "allow" or "deny"
    encrypted: bool = True
    note: str = ""


@dataclass
class Design:
    name: str
    hosts: List[Host]
    vms: List[VM]
    rules: List[Rule]
    default_action: str = "deny"
    edge: Tuple[str, ...] = ("FW1",)               # firewalls between the data centre and the outside
    arrays: Dict[str, bool] = field(default_factory=lambda: {"SAN1": False})   # storage array -> mirrored?
    vm_array: Dict[str, str] = field(default_factory=dict)
    hardening: Dict[str, bool] = field(default_factory=dict)
    placement: Dict[str, str] = field(default_factory=dict)

    def copy(self):
        import copy
        return copy.deepcopy(self)


HARDENING_ITEMS = {                      # item -> weight (share of the hardening score)
    "hypervisor_patched": 12, "mfa_admin": 12, "disk_encryption": 10, "immutable_backups": 12, "central_logging": 8,
    "secure_boot": 6, "rbac_least_privilege": 10, "vlan_isolation": 8, "intrusion_detection": 8, "time_sync_and_audit": 6, "snapshot_policy": 8,
}
