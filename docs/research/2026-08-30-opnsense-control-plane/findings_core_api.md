# OPNsense core control-plane API findings

Research date: 2026-08-30. Sources are OPNsense's official documentation and
upstream `opnsense/core` source only.

## Decision-relevant result

The earlier conclusion that interface assignment and IPv4 configuration require
a bespoke reconciler is no longer true for the current upstream `master`:
`Interfaces/Api/AssignmentController.php` and its `NetworkInterface.xml` model
now provide both. This is **not yet present in the published Interfaces API
reference**, so the installed OPNsense version must be checked before treating
it as an available production contract. The repository's reconciler should
feature-detect these read endpoints and fail closed if they return `404` or
`403`, rather than fall back to GUI automation or mutate `config.xml`.

## Read-only discovery and backup

All paths below are relative to `https://<firewall>/api` and authenticate with
a user-scoped API key and secret. OPNsense says API access uses local-user
authorization and that the user must have access to the API page/resource.

| Purpose | Method and endpoint | Parameters | Evidence and use |
|---|---|---|---|
| Discover local backup provider | `GET /core/backup/providers` | none | Returns providers, including `this` for the local firewall. Use first, do not assume its identifier. |
| List retained config backups | `GET /core/backup/backups/{host}` | `host` is the provider identifier, normally `this` | Returns each backup's `id`, time, description, username and size. |
| Download the newest retained backup | `GET /core/backup/download/{host}` | `host`; omit optional backup ID | Returns the newest `config-*.xml` in that provider. It is an XML export and can contain secrets. Store encrypted outside Git. |
| Download a specific backup | `GET /core/backup/download/{host}/{backup}` | `host`, exact `backup` ID returned by `backups` | Use the ID from the list, not a constructed filename. |
| Diff two retained backups | `GET /core/backup/diff/{host}/{backup1}/{backup2}` | `host`, two exact IDs | Read-only, useful to capture a pre-change baseline and verify the expected scope. |
| Runtime and declared interface inventory | `GET /interfaces/overview/interfaces_info/{details}` | optional `details`, use `true` for full detail | Returns assigned and unassigned devices, link state, addresses, routes, MACs, and each assigned interface's declared config. |
| One runtime interface record | `GET /interfaces/overview/get_interface/{if}` | physical device name, such as `igc0` or `vlan01` | Read-only detailed runtime record. |
| Export all interface inventory | `GET /interfaces/overview/export` | none | Returns JSON attachment containing the full detailed interface inventory. |
| Current VLAN model | `GET /interfaces/vlan_settings/search_item` | none | Published API reference documents it as `GET,POST`; records have UUIDs and VLAN fields. |
| One VLAN model record | `GET /interfaces/vlan_settings/get_item/{uuid}` | UUID from VLAN search | Use before a write and after apply. |
| Current assignment model, current upstream only | `GET /interfaces/assignment/search_item` | none | Source exposes the API, but the published reference does not list it yet. Treat availability as version-gated. |
| One assignment record, current upstream only | `GET /interfaces/assignment/get_item/{ifname}` | assignment identifier, such as `lan` or `opt1` | Source exposes it, but this needs a live canary on the installed firewall. |

Safe capture order: obtain the firewall certificate or CA, call `providers`,
`backups/this`, and `download/this/<returned-id>`; calculate a local hash and
save the encrypted export; then inventory interfaces and VLANs with GET-only
calls. Do not use `curl -k`: OPNsense documentation explicitly recommends a
valid certificate, and insecure TLS is only shown for testing.

## VLAN creation and apply

Published, documented API:

1. `POST /interfaces/vlan_settings/add_item` with a JSON object under `vlan`.
2. `POST /interfaces/vlan_settings/reconfigure` to apply the VLAN model.
3. Read back through `search_item`/`get_item/{uuid}` and runtime overview.

The upstream `Vlan.xml` marks these fields required:

```json
{
  "vlan": {
    "if": "<parent-device>",
    "tag": 10,
    "pcp": "0",
    "vlanif": "vlan01"
  }
}
```

`if` is the parent device, `tag` must be 1 through 4094 and unique per parent,
`pcp` is required and defaults to `0`, and `vlanif` must be unique. `proto`
(`802.1q` or `802.1ad`) and `descr` are optional. Preserve the returned UUID.
Do not change a VLAN's tag or device name after it is assigned, upstream rejects
that change.

## Interface assignment and static IPv4, upstream capability

Current upstream source exposes the following lifecycle:

1. `POST /interfaces/assignment/add_item` with body `{"interface": {...}}`.
2. `POST /interfaces/assignment/set_item/{ifname}` with the same envelope.
3. `POST /interfaces/assignment/reconfigure` to apply all pending assignments.
4. Verify with `GET /interfaces/assignment/get_item/{ifname}` and
   `GET /interfaces/overview/interfaces_info/true`.

The assignment model's required write fields are:

```json
{
  "interface": {
    "if": "vlan01",
    "lock": "1",
    "enable": "1",
    "disablevlanhwfilter": "0",
    "type4": "staticv4",
    "type6": "none",
    "ipaddr": "10.0.10.1/24",
    "dhcp6-ia-pd-len": "0"
  }
}
```

For an IPv4 static interface, `if`, `lock`, `enable`,
`disablevlanhwfilter`, `type4`, `type6`, and `dhcp6-ia-pd-len` are model-required.
`type4` must be `staticv4` and `ipaddr` uses CIDR notation with a required
netmask. `descr` is allowed and must match `^[a-z_0-9]{0,255}$`; `identifier`
and `pending_action` exist in the model but should be treated as controller
state, not declarative input. `ipaddr` is not globally required by the XML, but
is required by the desired `staticv4` behavior and must be read back after
apply. Obtain the exact field serialization from the installed WebGUI's Network
request before the first production write, as OPNsense's own API guide directs.

`reconfigure` invokes `interface apply`, persists the pending assignments into
the legacy interface config, then reloads the firewall filter. It is a
connectivity-affecting operation. The reconciler must stage an out-of-band or
console recovery path before calling it and never combine WAN, management, and
all LAN VLAN changes in one apply.

## Minimum safe reconciler contract

- Use a dedicated least-privilege local API user and a unique API key/secret
  for this reconciler. Its key secret is single-download only.
- Verify TLS using the firewall CA/certificate. Do not disable verification.
- Begin every run with the GET-only backup and inventory sequence above. Record
  the backup ID and SHA-256 of the downloaded export in CI artifacts, never in
  Git.
- Feature-detect `/interfaces/assignment/search_item`. If absent on the
  installed release, stop before a network mutation. The documented VLAN API
  alone is insufficient to assign or address a VLAN.
- For each write, use the response UUID/identifier, apply exactly one coherent
  change set, and read both model and runtime state afterward. Check the
  expected address, prefix length, link state, routes, and management
  reachability from an independent path.
- The core backup API downloads retained automatic backup files. It does not
  expose a documented API endpoint to create an immediate pre-change backup.
  Ensure OPNsense's configuration-history retention is enabled and retain the
  downloaded latest backup before writes. If an immediate backup is mandatory,
  validate a release-specific WebGUI operation manually before adding it to
  automation.

## Sources

- [OPNsense API usage guide](https://docs.opnsense.org/development/how-tos/api.html)
- [Official Core API reference, BackupController](https://docs.opnsense.org/development/api/core/core.html)
- [Official Interfaces API reference](https://docs.opnsense.org/development/api/core/interfaces.html)
- [Upstream AssignmentController](https://github.com/opnsense/core/blob/master/src/opnsense/mvc/app/controllers/OPNsense/Interfaces/Api/AssignmentController.php)
- [Upstream NetworkInterface assignment model](https://github.com/opnsense/core/blob/master/src/opnsense/mvc/app/models/OPNsense/Interfaces/NetworkInterface.xml)
- [Upstream VLAN controller](https://github.com/opnsense/core/blob/master/src/opnsense/mvc/app/controllers/OPNsense/Interfaces/Api/VlanSettingsController.php)
- [Upstream VLAN model](https://github.com/opnsense/core/blob/master/src/opnsense/mvc/app/models/OPNsense/Interfaces/Vlan.xml)
- [Upstream runtime OverviewController](https://github.com/opnsense/core/blob/master/src/opnsense/mvc/app/controllers/OPNsense/Interfaces/Api/OverviewController.php)
- [Upstream BackupController](https://github.com/opnsense/core/blob/master/src/opnsense/mvc/app/controllers/OPNsense/Core/Api/BackupController.php)
