# TL-SG108E port map

The switch is managed at `10.0.10.2/24` with gateway `10.0.10.1`.

| Port | Role | Untagged VLAN | Tagged VLANs | PVID |
|---|---|---:|---|---:|
| 1 | Trusted client access | 20 | | 20 |
| 2 | Management access | 10 | | 10 |
| 3 | OPNsense trunk | | 10, 20, 30, 40, 50, 60 | 1 |
| 4 | CLI ar9070 unit 2 (`homelab-03`) | 30 | | 30 |
| 5 | HP Mini infrastructure | 30 | | 30 |
| 6 | AdGuard and NetBird appliance | 30 | 60 | 30 |
| 7 | CLI ar9070 unit 1 (`homelab-02`) | 30 | | 30 |
| 8 | NAS (`nas-01`) | 30 | | 30 |

The hardware-reserved default VLAN 1 remains untagged on all ports in this switch firmware. No access port uses PVID 1, and the target network does not use VLAN 1 for client traffic.

VLAN 50 remains tagged on the OPNsense trunk but has no access port while the NAS occupies an infrastructure port. Restore port 4 to untagged VLAN 50 after additional switch capacity is installed.
