# OPNsense 26.7 API validation

The router was upgraded to OPNsense 26.7.1_1. TLS-verified API checks confirmed:

- `GET /api/interfaces/assignment/search_item` returns HTTP 200 and three records.
- `GET /api/interfaces/assignment/get_item/{identifier}` returns only assignment-model fields: `if`, `descr`, `icon`, `identifier`, `lock`, and `optgroup`.
- `GET /api/interfaces/vlan_settings/search_item` returns one existing VLAN and confirms `igb0` as the physical trunk parent.
- `GET /api/kea/dhcpv4/search_subnet`, `search_reservation`, and `/api/firewall/filter/search_rule` return UUID-bearing resource lists.
- `GET /api/unbound/settings/search_forward` is the current forwarding endpoint. The previous `/api/unbound/forward/search_forward` route returns 404.

## Revised ownership boundary

The released 26.7 assignment model does not define static IPv4 fields. The assignment endpoints persist device assignment metadata, but silently discard fields such as `type4` and `ipaddr`. Full L3 fields exist on the upstream development branch and are not a production contract for 26.7.

OpenTofu owns VLAN devices, Kea DHCP objects, MVC firewall rules, and supported Unbound objects. The Python reconciler owns interface assignment metadata and verifies the complete explicit L3 desired state against runtime overview data. On 26.7 it fails closed on L3 drift instead of reporting success after an ineffective API write.
