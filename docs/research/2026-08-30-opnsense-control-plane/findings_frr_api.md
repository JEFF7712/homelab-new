# OPNsense FRR BGP API findings

## Scope and compatibility

The `os-frr` plugin exposes the BGP controller at `/api/quagga/bgp/*`, its service lifecycle at `/api/quagga/service/*`, and FRR runtime diagnostics at `/api/quagga/diagnostics/*`. These are documented OPNsense API resources, not GUI-only internals. Pin the installed OPNsense and `os-frr` versions in the reconciler's tested compatibility matrix, then fail closed if the plugin or required endpoints are absent.

OPNsense API requests use HTTP Basic authentication with the API key as username and secret as password. `GET` reads state; mutating actions are `POST` with an `application/json` body. Grant the API user only the Quagga/FRR privileges required by these endpoints.

Sources:

- [OPNsense API reference](https://docs.opnsense.org/development/api.html)
- [Official Quagga API resource index](https://docs.opnsense.org/development/api/plugins/quagga.html)
- [os-frr BGP model](https://github.com/opnsense/plugins/blob/master/net/frr/src/opnsense/mvc/app/models/OPNsense/Quagga/BGP.xml)
- [os-frr BGP API controller](https://github.com/opnsense/plugins/blob/master/net/frr/src/opnsense/mvc/app/controllers/OPNsense/Quagga/Api/BgpController.php)
- [os-frr diagnostics API controller](https://github.com/opnsense/plugins/blob/master/net/frr/src/opnsense/mvc/app/controllers/OPNsense/Quagga/Api/DiagnosticsController.php)

## Desired-state writes

| Purpose | Method and endpoint | JSON body root | Notes |
|---|---|---|---|
| Read complete global BGP desired state | `GET /api/quagga/bgp/get` | n/a | Response root is `bgp`. Use before mutation and after it for read-after-write verification. |
| Set global BGP desired state | `POST /api/quagga/bgp/set` | `bgp` | The mutable-model base controller explicitly reads `POST["bgp"]`. |
| List stored neighbors | `GET /api/quagga/bgp/search_neighbor` | n/a | Also accepts `POST`; GET is adequate for the reconciler's discovery path. |
| Read one stored neighbor | `GET /api/quagga/bgp/get_neighbor/{uuid}` | n/a | UUID comes from `search_neighbor` or the result of `add_neighbor`. |
| Add neighbor | `POST /api/quagga/bgp/add_neighbor` | `neighbor` | The controller explicitly reads `POST["neighbor"]`. |
| Update neighbor | `POST /api/quagga/bgp/set_neighbor/{uuid}` | `neighbor` | Reuse the existing UUID, do not delete/recreate an established peer merely to change attributes. |
| Delete neighbor | `POST /api/quagga/bgp/del_neighbor/{uuid}` | none | Reconcile deletes only after the desired set is known and the management path is safe. |
| Apply generated FRR configuration | `POST /api/quagga/service/reconfigure` | none | Required after persisted BGP changes to make the running daemon converge. |
| Check FRR service | `GET /api/quagga/service/status` | n/a | Verify the service is running after reconfigure. |

Minimal intended payloads, with actual ASNs and addresses supplied by the inventory:

```json
{
  "bgp": {
    "enabled": "1",
    "asnumber": "<opnsense-asn>",
    "routerid": "<stable-opnsense-ipv4>",
    "networkimportcheck": "1",
    "enforce_first_as": "1"
  }
}
```

```json
{
  "neighbor": {
    "enabled": "1",
    "description": "cilium-bgp-control-plane",
    "address": "<node-or-virtual-router-ip>",
    "remoteas": "<cilium-asn>"
  }
}
```

The API model represents booleans as string values (`"1"`/`"0"`) in its normal JSON form. Before treating either example as a final full-object update, the reconciler should read the live object and retain explicit desired values for every safety-relevant field. It must reject a response containing validation errors or `result: failed`, even if the transport status is 200, because OPNsense APIs can serialize failures in a successful HTTP response.

## Model constraints relevant to Cilium peering

Global BGP fields:

- `enabled` is required.
- `asnumber` is required and must be an integer from `1` through `4294967295`.
- `routerid`, if supplied, must match an IPv4 dotted-quad pattern. Use a stable management address, not a DHCP address.
- `distance`, if supplied, must be `1` through `255`.
- `networkimportcheck`, `enforce_first_as`, `graceful`, and `logneighborchanges` are Boolean fields.

Neighbor fields:

- `enabled` is required; `address` is required and is a `NetworkField`.
- `remoteas` and optional `localas` must be integers from `1` through `4294967295`.
- `remote_as_mode` supports an explicit remote ASN or the `internal`/`external` alternatives. For Cilium, use explicit `remoteas` unless the architecture deliberately requires the semantic alternatives.
- `updatesource` and `linklocalinterface` are enabled-interface references. Use neither for directly connected IPv4 VLAN peers unless an interface-source design is deliberately selected.
- The model permits `password`, but it is plaintext configuration material. If BGP MD5 is enabled, place it only in SOPS-encrypted reconciler input. The model also requires `localip` whenever a password is set.

An upstream issue reports that `localip` is not translated into FRR `update-source`; `updatesource` is the setting intended to generate that behavior. Treat this as a version-specific risk to verify against the pinned `os-frr` release, rather than relying on `localip` as deterministic source-address control. It does not affect direct same-VLAN Cilium BGP sessions. [Upstream issue #5362](https://github.com/opnsense/plugins/issues/5362)

## Runtime proof endpoints

Use the following after every apply, and make them acceptance checks rather than best-effort telemetry:

| Proof | Method and endpoint | Success condition |
|---|---|---|
| Service converged | `GET /api/quagga/service/status` | FRR reports running. |
| Peer sessions | `GET /api/quagga/diagnostics/bgpsummary` | Every intended Cilium peer is present and established. Inspect the returned FRR JSON, not just HTTP status. |
| Peer details | `GET /api/quagga/diagnostics/bgpneighbors` | Peer address, ASN, and negotiated state match the intended design. |
| IPv4 BGP RIB | `GET /api/quagga/diagnostics/search_bgproute4` | Expected Cilium LoadBalancer `/32` routes are present with expected next hops. |
| IPv6 BGP RIB, only if designed | `GET /api/quagga/diagnostics/search_bgproute6` | Expected IPv6 routes are present. |
| Generated running configuration | `GET /api/quagga/diagnostics/generalrunningconfig` | Optional diagnostic evidence that generated BGP configuration contains only declared peers/settings. Do not log secrets. |

`bgpsummary` and `bgpneighbors` return the FRR JSON response under a top-level `response` property. The route endpoints return an OPNsense grid-style result after parsing FRR route data. Persist only redacted structured evidence, never raw running configuration when MD5 credentials are enabled.

## Recommended reconciliation transaction

1. Read global desired state and neighbor inventory.
2. Validate desired ASNs, peer addresses, and firewall-management reachability before writes.
3. Write global BGP settings, then add/update/deactivate neighbors deterministically by stored UUID.
4. Read persisted objects again and compare to the canonical desired object.
5. Call `POST /api/quagga/service/reconfigure` once.
6. Poll service status, summary, neighbor details, and expected BGP routes until bounded success or timeout.
7. On failed proof, report the failed structured API body and retain the encrypted pre-change OPNsense backup for human-directed recovery. Do not blindly retry a configuration change that could remove the caller's management route.
