# OpenTofu provider import findings

Scope: `browningluke/opnsense` at upstream `main` commit
`33c2a03c2bc1a7339cb5aa5b611e15014e27f7ba` (the v0.26.0 release commit).
The provider is still pre-1.0, so pin an exact version before writing managed
state and review release notes on upgrades.

## Import rule

All item resources below import by the OPNsense API UUID, not by VLAN tag,
CIDR, description, interface, or IP address. Terraform/OpenTofu import blocks
and the imperative import command have identical IDs:

```hcl
import {
  to = RESOURCE.ADDRESS
  id = "<opnsense-resource-id>"
}
```

```console
tofu import RESOURCE.ADDRESS <opnsense-resource-id>
```

The provider data sources also require an already-known UUID, so they cannot
discover existing objects. The read-only inventory/reconciler must list each
OPNsense controller first, preserve UUID-to-logical-name mappings, then
generate resource definitions and imports.

## Managed resources

| Concern | Resource | Required configuration | Import ID |
|---|---|---|---|
| VLAN device | `opnsense_interfaces_vlan` | `parent`, `tag`; optional `description`, `device`, `priority` | VLAN UUID |
| Kea DHCPv4 subnet | `opnsense_kea_dhcpv4_subnet` | `subnet`; optional pools, routers, DNS, domain, NTP, static routes, and `auto_collect` | subnet UUID |
| Kea DHCPv4 reservation | `opnsense_kea_dhcpv4_reservation` | `subnet_id`, `ip_address`, `mac_address`; optional `hostname`, `description` | reservation UUID |
| Firewall rule | `opnsense_firewall_filter` | `interface` and `filter`; optional `sequence`, `enabled`, categories and state/routing controls | rule UUID |
| Unbound singleton | `opnsense_unbound_settings` | singleton resource, blocks such as `general`, `forwarding`, `acls`, `advanced` | literal `unbound_settings` |
| Unbound domain forward | `opnsense_unbound_forward` | `domain`, `server_ip`; optional `server_port`, `type`, `verify_cn`, `enabled` | forward UUID |

For the VLANs approved in this architecture, `parent` must be the physical
trunk device name reported by OPNsense, not its friendly interface assignment.
VLAN resource creation only creates the device. This resource cannot assign it
to an OPNsense interface or set its IPv4 address, so those operations remain
the API-reconciler workstream.

For Kea, make `auto_collect = false` when OpenTofu must own `routers`,
`dns_servers`, and `ntp_servers`: the provider documentation says those values
are ignored when it is true (the default). Reservations must reference the
managed/imported subnet UUID, not the CIDR.

Firewall rules use OPNsense interface identifiers such as `lan` or `opt1` in
`interface.interface`. An empty set is a floating rule. Preserve `sequence`
during import, since it is rule ordering; do not recreate legacy rules solely
to obtain a preferred order.

`opnsense_unbound_settings` is mandatory to import before management. Its
`forwarding.enabled` controls use of system nameservers and overrides generic
forwards, except domain-specific forward entries. Use `opnsense_unbound_forward`
for the explicit AdGuard forwarding route. A DoT forward requires
`type = "dot"` and a `verify_cn`; query forwarding defaults to port 53.

## Sources

- Provider README and coverage matrix: https://github.com/browningluke/terraform-provider-opnsense/tree/33c2a03c2bc1a7339cb5aa5b611e15014e27f7ba
- VLAN resource and UUID import: https://github.com/browningluke/terraform-provider-opnsense/blob/33c2a03c2bc1a7339cb5aa5b611e15014e27f7ba/docs/resources/interfaces_vlan.md
- Kea subnet resource and UUID import: https://github.com/browningluke/terraform-provider-opnsense/blob/33c2a03c2bc1a7339cb5aa5b611e15014e27f7ba/docs/resources/kea_dhcpv4_subnet.md
- Kea reservation resource and UUID import: https://github.com/browningluke/terraform-provider-opnsense/blob/33c2a03c2bc1a7339cb5aa5b611e15014e27f7ba/docs/resources/kea_dhcpv4_reservation.md
- Firewall filter resource and UUID import: https://github.com/browningluke/terraform-provider-opnsense/blob/33c2a03c2bc1a7339cb5aa5b611e15014e27f7ba/docs/resources/firewall_filter.md
- Unbound settings singleton import: https://github.com/browningluke/terraform-provider-opnsense/blob/33c2a03c2bc1a7339cb5aa5b611e15014e27f7ba/docs/resources/unbound_settings.md
- Unbound forward resource and UUID import: https://github.com/browningluke/terraform-provider-opnsense/blob/33c2a03c2bc1a7339cb5aa5b611e15014e27f7ba/docs/resources/unbound_forward.md
