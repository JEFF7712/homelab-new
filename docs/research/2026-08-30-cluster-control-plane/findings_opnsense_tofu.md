# OPNsense and OpenTofu capability check

Checked 2026-08-30 against the maintained community provider source. The viable
provider is [`browningluke/opnsense`](https://registry.terraform.io/providers/browningluke/opnsense/latest), currently 0.26.0. It is compatible with OpenTofu because it is a Terraform plugin, but it is not an OPNsense-maintained provider. Its maintainer explicitly says it is pre-1.0, schemas may break, and it is not recommended for production:
[`README`](https://github.com/browningluke/terraform-provider-opnsense#terraform-provider-for-opnsense).

## Required design surface

| Requirement | Provider status | Resource(s) | Important limitation |
|---|---|---|---|
| Create 802.1Q VLAN devices | Supported | `opnsense_interfaces_vlan` | It creates the VLAN device only. The provider does **not** support interface assignment or L3 interface configuration, so assigning `vlanX` to an OPNsense interface and setting its gateway/address remains manual/API-custom work. [VLAN docs](https://github.com/browningluke/terraform-provider-opnsense/blob/main/docs/resources/interfaces_vlan.md), [coverage table](https://github.com/browningluke/terraform-provider-opnsense#current-api-coverage). |
| DHCPv4 scopes and pools | Supported | `opnsense_kea_dhcpv4_subnet` | Kea subnets carry pools, routers, DNS servers, and other DHCP options. This requires the Kea DHCP service, not the legacy ISC DHCP configuration. [Subnet docs](https://github.com/browningluke/terraform-provider-opnsense/blob/main/docs/resources/kea_dhcpv4_subnet.md). |
| DHCPv4 reservations | Supported | `opnsense_kea_dhcpv4_reservation` | A reservation refers to the provider-managed Kea subnet UUID. [Reservation docs](https://github.com/browningluke/terraform-provider-opnsense/blob/main/docs/resources/kea_dhcpv4_reservation.md). |
| Firewall policy | Supported | `opnsense_firewall_alias`, `opnsense_firewall_category`, `opnsense_firewall_filter`, NAT resources | Filters and aliases are implemented; category has missing acceptance tests. Rule ordering must be intentionally set with `sequence`. [Filter docs](https://github.com/browningluke/terraform-provider-opnsense/blob/main/docs/resources/firewall_filter.md), [coverage table](https://github.com/browningluke/terraform-provider-opnsense#current-api-coverage). |
| Resolver configuration and forwarding | Supported | `opnsense_unbound_settings`, `opnsense_unbound_forward`, domain/host overrides | This is Unbound, not DNSmasq. `unbound_settings` is a singleton that must be imported before it can be managed. Forward entries can target AdGuard with `domain = ""` and `type = "query"`. [Unbound settings docs](https://github.com/browningluke/terraform-provider-opnsense/blob/main/docs/resources/unbound_settings.md), [forward docs](https://github.com/browningluke/terraform-provider-opnsense/blob/main/docs/resources/unbound_forward.md). |
| Cilium BGP peer | Partial and unsuitable as the sole control plane | `opnsense_quagga_bgp_neighbor`, prefix lists, route maps, AS paths, community lists | Neighbor resources exist, but the provider's own coverage table marks them and related policy resources as missing acceptance tests. More importantly, `Quagga/General` and `Quagga/Bgp` are unimplemented, so it cannot declaratively enable/configure the routing daemon or its local ASN/global BGP settings. [Neighbor docs](https://github.com/browningluke/terraform-provider-opnsense/blob/main/docs/resources/quagga_bgp_neighbor.md), [coverage table](https://github.com/browningluke/terraform-provider-opnsense#current-api-coverage). |

## Migration and ownership conclusion

Existing object-backed resources can be imported by their OPNsense UUID, including
VLANs, Kea subnets/reservations, firewall filters, forwarding entries, and BGP
neighbors. The provider docs give both import-block and CLI-import forms for
those resources. Import is mandatory for the singleton `opnsense_unbound_settings`
with fixed ID `unbound_settings`; destroy then removes only state, not upstream
DNS configuration. Sources: [VLAN import](https://github.com/browningluke/terraform-provider-opnsense/blob/main/docs/resources/interfaces_vlan.md#Import), [Unbound singleton/import](https://github.com/browningluke/terraform-provider-opnsense/blob/main/docs/resources/unbound_settings.md#singleton-behavior).

Do not promise that OpenTofu alone reconciles all of OPNsense. Use it for the
supported resources after a deliberate one-time import or clean rebuild. Keep a
small, explicitly versioned bootstrap/manual contract for interface assignment,
interface IPs, service enablement, and FRR global BGP settings. A custom provider
extension or a reviewed OPNsense API client is required before declaring those
gaps fully managed. Pin the provider version and run plans against a non-primary
firewall configuration before applying because the provider is pre-1.0.

## Rejected provider

`RyanNgWH/terraform-provider-opnsense` advertises OpenTofu compatibility, but its
repository declares OPNsense CE 25.7.8+ while also carrying stale compatibility
text and a far smaller, developing surface. It is not a better basis for this
design. [Repository README](https://github.com/RyanNgWH/terraform-provider-opnsense).
