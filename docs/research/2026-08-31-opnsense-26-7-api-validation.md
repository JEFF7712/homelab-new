# OPNsense 26.7 API validation

The router was upgraded to OPNsense 26.7.1_1. TLS-verified API checks confirmed:

- `GET /api/interfaces/assignment/search_item` returns HTTP 200 and three records.
- `GET /api/interfaces/assignment/get_item/{identifier}` returns only assignment-model fields: `if`, `descr`, `icon`, `identifier`, `lock`, and `optgroup`.
- `GET /api/interfaces/vlan_settings/search_item` returns one existing VLAN and confirms `igb0` as the physical trunk parent.
- `GET /api/kea/dhcpv4/search_subnet`, `search_reservation`, and `/api/firewall/filter/search_rule` return UUID-bearing resource lists.
- `GET /api/unbound/settings/search_forward` is the current forwarding endpoint. The previous `/api/unbound/forward/search_forward` route returns 404.

## Revised ownership boundary

The 26.7 assignment model accepts static IPv4 fields and its `reconfigure` action persists assignment changes. Its `get_item` response does not hydrate existing legacy L3 state, so it cannot support read-modify-write configuration. The reconciler must instead send complete explicit desired records, apply one coherent change set, and verify addresses from runtime interface overview data.

OpenTofu owns VLAN devices, Kea DHCP objects, MVC firewall rules, and supported Unbound objects. The Python reconciler owns interface assignments and explicit L3 configuration only after an explicit reviewed change plan. It must refuse a transaction that includes the management interface and every other LAN interface.
