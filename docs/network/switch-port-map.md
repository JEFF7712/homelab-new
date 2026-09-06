# TL-SG108E port map

The switch is managed at `10.0.10.2/24` with gateway `10.0.10.1`.

| Port | Role | Untagged VLAN | Tagged VLANs | PVID |
|---|---|---:|---|---:|
| 1 | Trusted WiFi via TP-Link RE505X AP | 20 | | 20 |
| 2 | Management access | 10 | | 10 |
| 3 | OPNsense trunk | | 10, 20, 30, 40, 50, 60 | 1 |
| 4 | CLI ar9070 unit 2 (`homelab-03`) | 30 | | 30 |
| 5 | HP Mini infrastructure | 30 | | 30 |
| 6 | AdGuard and NetBird appliance | 30 | 60 | 30 |
| 7 | CLI ar9070 unit 1 (`homelab-02`) | 30 | | 30 |
| 8 | NAS (`nas-01`) | 30 | | 30 |

The hardware-reserved default VLAN 1 remains untagged on all ports in this switch firmware. No access port uses PVID 1, and the target network does not use VLAN 1 for client traffic.

VLAN 50 remains tagged on the OPNsense trunk but has no access port while the NAS occupies an infrastructure port. Restore port 4 to untagged VLAN 50 after additional switch capacity is installed.

## Port 1 WiFi AP (TP-Link RE505X, AX1500)

Wired to switch port 1 in Access Point mode. All WiFi clients land on trusted VLAN 20 (DHCP/DNS from OPNsense). Single Gigabit uplink, no VLAN tagging on the AP.

- Management IP: `10.0.20.2/24`, gateway `10.0.20.1`, DNS `10.0.20.1`
- Mode: Access Point (not Range Extender), DHCP server off, WPS off, guest network off
- Wireless: shared SSID on 2.4 GHz + 5 GHz (Smart Connect), WPA2-PSK AES minimum (WPA2/WPA3 mixed if offered)
- 5 GHz: `802.11a/n/ac/ax mixed`, OFDMA/MU-MIMO enabled, width/channel Auto (80 MHz, 36-48 if pinned)
- 2.4 GHz: enabled, 20 MHz, channel 1/6/11 (Auto to start)
