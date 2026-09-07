# Cloudflare Tunnel `homelab`

Remote-configured tunnel fronting the new k3s cluster. Dashboard edits apply directly, so record version and order here.

## Identity

- Name: `homelab`
- ID: `0f08d8c5-6f2c-409e-ba80-dc0601e0227e`
- Config source: `cloudflare` (Zero Trust dashboard, not `gitops/`)
- Connectors: 2 replicas from `gitops/cloudflare/tunnel.yaml` (`cloudflared 2026.8.3`)
- Health: `healthy`, 8 connections on `ord10, mci03, ord15, ord06, mci01, ord02`
- Public origin IP seen by edge: `50.93.213.22` (connector pods live in `10.0.30.0/24`)

## Traffic path for `photos.rupan.dev`

Internet -> Cloudflare edge -> `cloudflared` pods -> `http://immich-server.immich:80` (in-cluster Service DNS) -> `Service immich-server:80 -> 2283`.

Do not point tunnel origins at the Gateway LB VIP (`10.0.40.12`): Cilium implements it as a local redirect that only answers in host network namespaces, so `cloudflared` (pod netns) blackholes dialing it. Use in-cluster Service DNS names, consistent with the other new-cluster entries. The `HTTPRoute immich/immich` still exists for Gateway-routed access, but the tunnel bypasses it.

Related manifests:

- `gitops/cloudflare/tunnel.yaml`
- `gitops/immich/route.yaml` (`photos.rupan.dev`, inert while `Gateway homelab` is parked)
- `gitops/immich/server.yaml`

## Ingress order (v62, 2026-09-07)

Cloudflare evaluates top to bottom, first match wins. Keep specifics first, wildcard second to last, catch-all last.

1. `glance.rupan.dev -> http://glance:8080`
2. `pihole.rupan.dev -> http://pihole:80`
3. `api.rupan.dev -> http://rupan-api:9000`
4. `homelab.rupan.dev -> http://homelab-api:9200`
5. `photos.rupan.dev -> http://immich-server.immich:80`
6. `www.pulseagent.dev -> http://pulse-svc.pulse:80`
7. `ism.rupan.dev -> http://ism-svc.ism:80`
8. `nix-agent.rupan.dev -> http://nixagent-svc.nixagent:80`
9. `rupanism.rupan.dev -> http://rupanism-svc.rupanism:80`
10. `spatia.rupan.dev -> http://spatia-svc.spatia:80`
11. `demo.rupan.dev -> http://cr-demo-svc.cr-demo:80`
12. `soluble.rupan.dev -> http://soluble-rupan-svc.soluble-rupan:80`
13. `photo.rupan.dev -> http://photography-svc.photography:80`
14. `majorfinder.rupan.dev -> http://majorfinder-svc.majorfinder:80`
15. `notes.rupan.dev -> http://quartz-notes.obsidian.svc.cluster.local:80`
16. `ntfy.rupan.dev -> http://ntfy-ntfy.observability.svc.cluster.local:80`
17. `obsidian.rupan.dev -> http://couchdb.obsidian.svc.cluster.local:5984`
18. `*.rupan.dev -> https://10.0.20.180:443` (`noTLSVerify: true`)
19. `distrojeff.com -> http://distrojeff-site-svc.distrojeff:80`
20. `apollinestore.com -> http://apolline-svc.apolline:80`
21. `darkbitapparel.com -> http://darkbit-svc.darkbit:80`
22. `sandhufiles.site -> https://10.0.20.180:443` (`noTLSVerify: true`)
23. `pulseagent.dev -> http://pulse-svc.pulse:80`
24. `http_status:404`

Do not place a specific `*.rupan.dev` match below the wildcard. `photos` was briefly at position 11 (v50) and would have matched the wildcard at position 6. Moved above the wildcard in v51.

## Add a new-cluster hostname

1. Add tunnel ingress `{hostname, service: http://<service>.<namespace>:<port>}` above `*.rupan.dev` via dashboard or API `PUT /accounts/{id}/cfd_tunnel/{id}/configurations`. (Skip the `HTTPRoute`/`Gateway` step while `Gateway homelab` is parked; `3985d4f` and `98ef8df` removed it.)
2. Confirm DNS `CNAME <host> -> <tunnel-id>.cfargotunnel.com` exists (dashboard creates it on hostname add).
3. Verify: `GET cfd_tunnel/{id}` is `healthy` with connections on `ord/mci`, `GET configurations` shows the new hostname with the in-cluster service URL in the expected position.

## Known gap

Tunnel ingress is still dashboard managed. Per ownership (`tofu/` owns API-managed systems), codify as `cloudflare_tunnel_config` under `tofu/` (only `tofu/opnsense/` exists today) to prevent drift.
