# Switch and access-point port map

OPNsense is the only router, DHCP server, DNS provider, and inter-VLAN firewall.
The wall run is an 802.1Q transit link: VLAN 99 carries the ISP handoff to the
OPNsense WAN NIC, while VLANs 10 and 20 provide downstairs management and
trusted-client access. VLAN 99 never reaches the OPNsense LAN trunk.

## Upstairs TL-SG108E

Management: `10.0.10.2/24`, gateway `10.0.10.1`.

| Port | Role | Untagged VLAN | Tagged VLANs | PVID |
|---|---|---:|---|---:|
| 1 | OPNsense WAN NIC | 99 | | 99 |
| 2 | OPNsense LAN NIC | | 10, 20, 30, 40, 50, 60 | 1 |
| 3 | Downstairs wall trunk | | 10, 20, 99 | 1 |
| 4 | Unmanaged cluster access switch | 30 | | 30 |
| 5 | NAS (`nas-01`) | 30 | | 30 |
| 6 | AdGuard and NetBird appliance | 30 | 60 | 30 |
| 7 | Upstairs TP-Link RE505X AP | 20 | | 20 |
| 8 | Management access | 10 | | 10 |

The hardware-reserved default VLAN 1 remains untagged on every port in this
switch firmware. Only trunk ports use PVID 1. No access port carries
production traffic in VLAN 1.

The unmanaged cluster switch uses a single uplink on port 4. Its attached HP
Mini and two CLI ar9070 nodes share VLAN 30 and that one gigabit uplink.

## Downstairs managed switch

Management: `10.0.10.3/24`, gateway `10.0.10.1`.

| Port | Role | Untagged VLAN | Tagged VLANs | PVID |
|---|---|---:|---|---:|
| 1 | ISP/modem handoff | 99 | | 99 |
| 2 | Upstairs wall trunk | | 10, 20, 99 | 1 |
| 3 | Downstairs AP/router in AP mode | 20 | | 20 |
| 4 | Management access | 10 | | 10 |
| 5 | Trusted-client spare | 20 | | 20 |

VLAN 99 is Layer-2 WAN transit only. Do not connect a client or AP to port 1,
and do not connect the downstairs switch to the upstairs switch by any path
other than the wall trunk on port 2.

## Access points

Both APs are ordinary VLAN 20 clients. They are not routers and do not tag
their uplinks.

| Location | Device | Switch port | Addressing | Required mode |
|---|---|---:|---|---|
| Upstairs | TP-Link RE505X (AX1500) | TL-SG108E port 7 | Static `10.0.20.2/24` | Access Point; DHCP, WPS, and guest network off |
| Downstairs | NETGEAR R6400v2 | Downstairs port 3 | DHCP lease, last observed `10.0.20.145` | Access Point; DHCP, NAT, and routing off |

Use a LAN port, never the WAN/Internet port, for each AP uplink. Both APs use
the same SSID and security settings for client roaming. Assign different
non-overlapping radio channels where their coverage overlaps. Reserve the
downstairs AP's DHCP address in OPNsense by MAC address when its management
address needs to remain stable.
