# OPNsense 26.7 API validation

The router was upgraded to OPNsense 26.7.1_1. TLS-verified API checks confirmed:

- `GET /api/interfaces/assignment/search_item` returns HTTP 200 and three records.
- `GET /api/interfaces/assignment/get_item/{identifier}` returns only assignment-model fields: `if`, `descr`, `icon`, `identifier`, `lock`, and `optgroup`.
- `GET /api/interfaces/vlan_settings/search_item` returns one existing VLAN and confirms `igb0` as the physical trunk parent.
- `GET /api/kea/dhcpv4/search_subnet`, `search_reservation`, and `/api/firewall/filter/search_rule` return UUID-bearing resource lists.
- `GET /api/unbound/settings/search_forward` is the current forwarding endpoint. The previous `/api/unbound/forward/search_forward` route returns 404.

## Revised ownership boundary

The 26.7 assignment API safely manages interface assignment metadata and its `reconfigure` action persists assignment changes. It does not expose per-interface IPv4 configuration in the model returned by `get_item`. Static L3 addresses therefore remain a one-time console/WebGUI bootstrap concern until OPNsense publishes a stable per-interface L3 API.

OpenTofu owns VLAN devices, Kea DHCP objects, MVC firewall rules, and supported Unbound objects. The Python reconciler may manage assignment metadata only after an explicit reviewed change plan. It must not claim ownership of IPv4 addressing, gateways, or routes.
