# Node-RED Setup Runbook

Node-RED runs as a sibling Deployment in the `home-assistant` namespace and integrates with Home Assistant in both directions. This runbook covers first-time setup, secret bootstrapping, and the rules for which automations live where.

## Topology

```
+-----------------------+         +------------------------+
|  Home Assistant       |  <----> |  Node-RED              |
|  k3s, hostNetwork     |  REST + |  Deployment in-cluster |
|  port 8123            |  WS     |  port 1880 (BGP)       |
|  bgp-advertise: true  |         |  bgp-advertise: true   |
+-----------------------+         +------------------------+
                                          |
                                          v
                                  nodered-data PVC
                                  (flows.json, flows_cred.json,
                                   settings.js, node_modules/)
```

Node-RED is reachable in-cluster at `nodered.home-assistant.svc.cluster.local:1880` and externally via the same BGP-advertised IP as Home Assistant on port 1880.

## First-time bootstrap

After `git push`, Flux will reconcile the new resources. Before the Node-RED Pod can come up healthy, four secrets must exist in SOPS:

| SOPS key                         | Used as                                    | How to generate                                                                              |
| -------------------------------- | ------------------------------------------ | -------------------------------------------------------------------------------------------- |
| `NODERED_ADMIN_USERNAME`         | Node-RED login user + HA integration user  | Pick a username, store as plaintext                                                          |
| `NODERED_ADMIN_PASSWORD`         | HA `nodered` integration basic-auth        | Pick a strong password, store as plaintext                                                   |
| `NODERED_ADMIN_PASSWORD_HASH`    | Node-RED `adminAuth` (bcrypt hash)         | `htpasswd -bnBC 12 "" '<password>' \| tr -d ':\n'` and store the bcrypt output               |
| `NODERED_CREDENTIAL_SECRET`      | Encrypts `flows_cred.json`                 | `openssl rand -hex 32` and store                                                              |

Without these, the init container fails to render `settings.js` and the Pod crash-loops. The first three are paired: the plaintext password must equal the plaintext used to compute the bcrypt hash. The credential secret is stable across deploys; rotating it invalidates all `flows_cred.json` entries.

To bootstrap from scratch:

```sh
# 1. Generate credentials
nodered_user="admin"
nodered_pass="$(openssl rand -base64 32 | tr -d '\n+/=' | head -c 40)"
nodered_hash="$(htpasswd -bnBC 12 "" "$nodered_pass" | tr -d ':\n')"
nodered_secret="$(openssl rand -hex 32)"

# 2. Push the secrets to the GitLab project that backs ClusterSecretStore gitlab-project.
glab variable set NODERED_ADMIN_USERNAME "$nodered_user" \
  -R JEFF7712/homelab-new --protected --scope '*'
glab variable set NODERED_ADMIN_PASSWORD "$nodered_pass" \
  -R JEFF7712/homelab-new --protected --masked --scope '*'
glab variable set NODERED_ADMIN_PASSWORD_HASH "$nodered_hash" \
  -R JEFF7712/homelab-new --protected --scope '*'
glab variable set NODERED_CREDENTIAL_SECRET "$nodered_secret" \
  -R JEFF7712/homelab-new --protected --masked --scope '*'
```

GitLab refuses to mask values that don't pass its secret-shape regex. The username (`admin`) and the bcrypt hash (`$2y$12$...`) fall into that bucket, so they are stored unmasked; the plaintext password and the credential secret are masked. None of the four are recoverable to a usable password from the bcrypt hash alone, so this is acceptable.

```sh
# 3. Force reconciliation
flux reconcile kustomization home-assistant --with-source

# 4. Watch rollout
kubectl -n home-assistant rollout status deploy/nodered
```

ExternalSecret refreshes every hour. To force an immediate refresh:

```sh
kubectl -n home-assistant annotate externalsecret nodered-secrets \
  force-sync="$(date +%s)" --overwrite
```

## Reaching the editor

- In-cluster: `http://nodered.home-assistant.svc.cluster.local:1880`
- LAN/VPN: BGP-advertised IP on port 1880 (same IP as Home Assistant)
- Public: not exposed; front it with Cloudflare Tunnel or HA's existing reverse proxy when ready

The first login prompts for the username and password from `NODERED_ADMIN_USERNAME` / `NODERED_ADMIN_PASSWORD`.

## Connecting Node-RED to Home Assistant

1. Open the editor and choose **Palette → Install**, search for `node-red-contrib-home-assistant-websocket`, install it.
2. Add an `ha-server` config node:
   - **Host**: `http://home-assistant.home-assistant.svc.cluster.local:8123`
   - **Name**: anything (e.g. `Home Assistant`)
   - **Token**: a long-lived access token from the HA user profile page
3. Use `ha-state-changed` / `ha-call-service` / `ha-tag` nodes in flows. Tokens are stored encrypted in `flows_cred.json` using `NODERED_CREDENTIAL_SECRET`.

## Where automations live

Keep simple, declarative automations (single trigger, one or two conditions, one action) as Home Assistant YAML under `home-assistant/automations/`. The HA tooling (`just ha-validate`, `just ha-diff`, `just ha-adopt`) is the only practical way to manage them at this size and they remain git-diffable.

Move an automation to Node-RED when any of these become true:

- The `choose:` block has more than two branches.
- It depends on timers, delays, or rate-limiting logic that HA expresses awkwardly.
- It bridges MQTT, HTTP, or another broker alongside HA.
- It needs JavaScript to compute a value (e.g. weather, presence, battery thresholds).

First candidates: `bedroom_lights_evening_presence` and `away_lights_off_restore`, which already exceed two `choose:` branches.

## Backup and recovery

`nodered-data` lives on the NFS-cluster PVC and is included in the cluster's NFS snapshots. To rebuild from scratch:

1. Re-create the four SOPS secrets.
2. Flux will reconcile the Deployment; the init container renders `settings.js`, and the existing `flows.json` / `flows_cred.json` on the PVC seed the editor.

If the PVC is lost, flows must be re-imported from Git (`home-assistant/node-red/flows.json` is the bootstrap). Authored changes in the UI that were not committed to Git are lost.

## Validating locally

```sh
just check-changed
nix develop ./flake -c python -m unittest tests.test_node_red_setup -v
yamllint gitops/home-assistant
bash scripts/checks/gitops.sh
```
