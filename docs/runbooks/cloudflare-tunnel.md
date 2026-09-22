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

Do not point tunnel origins at a Cilium LB VIP (`10.0.40.x`): Cilium implements it as a local redirect that only answers in host network namespaces, so `cloudflared` (pod netns) blackholes dialing it. Use in-cluster Service DNS names, consistent with the other new-cluster entries. The Gateway API layer was removed (tunnel is the public edge; NetBird covers remote LAN access), so the tunnel is the only path, not a bypass.

Related manifests:

- `gitops/cloudflare/tunnel.yaml`
- `gitops/immich/server.yaml`

## Ingress order (v73, 2026-09-20)

Cloudflare evaluates top to bottom, first match wins. Keep specifics first, catch-all last.

Cutover completed: `rupan.dev` and `www.rupan.dev` route to `http://rupan-dev-svc.rupan-dev:80`
via the homelab tunnel, backed by local image `registry.rupan.dev/apps/rupan-dev`. DNS apex and
`www` point to the tunnel CNAME (`0f08d8c5-6f2c-409e-ba80-dc0601e0227e.cfargotunnel.com`) with
Cloudflare Access public bypass configured.

1. `photos.rupan.dev -> http://immich-server.immich:80`
2. `www.pulseagent.dev -> http://pulse-svc.pulse:80`
3. `pulseagent.dev -> http://pulse-svc.pulse:80`
4. `ism.rupan.dev -> http://ism-svc.ism:80`
5. `nix-agent.rupan.dev -> http://nixagent-svc.nixagent:80`
6. `rupanism.rupan.dev -> http://rupanism-svc.rupanism:80`
7. `spatia.rupan.dev -> http://spatia-svc.spatia:80`
8. `demo.rupan.dev -> http://cr-demo-svc.cr-demo:80`
9. `soluble.rupan.dev -> http://soluble-rupan-svc.soluble-rupan:80`
10. `photo.rupan.dev -> http://photography-svc.photography:80`
11. `majorfinder.rupan.dev -> http://majorfinder-svc.majorfinder:80`
12. `notes.rupan.dev -> http://quartz-notes.obsidian.svc.cluster.local:80`
13. `ntfy.rupan.dev -> http://ntfy-ntfy.observability.svc.cluster.local:80`
14. `obsidian.rupan.dev -> http://couchdb.obsidian.svc.cluster.local:5984`
15. `renovate-approve.rupan.dev -> http://renovate-approval-webhook.automation:8080`
16. `renovate-status.rupan.dev -> http://renovate-dashboard.automation:8080`
17. `ha.rupan.dev -> http://home-assistant.home-assistant:8123`
18. `rupan.dev -> http://rupan-dev-svc.rupan-dev:80`
19. `www.rupan.dev -> http://rupan-dev-svc.rupan-dev:80`
20. `grafana.rupan.dev -> http://kube-prometheus-stack-grafana.observability.svc.cluster.local:80`
21. `distrojeff.com -> http://distrojeff-site-svc.distrojeff:80`
22. `apollinestore.com -> http://apolline-svc.apolline:80`
23. `darkbitapparel.com -> http://darkbit-svc.darkbit:80`
24. `pulseagent.dev -> http://pulse-svc.pulse:80`
25. `flux-wh-33b0c8004348.rupan.dev -> http://webhook-receiver.flux-system:80` (Flux GitLab push receiver, 2026-09-20; Access app `flux-webhook-bypass` reused Bypass policy, wildcard `*` app would otherwise force login)
26. `http_status:404`

Removed 2026-09-15 (v72):
- `*.rupan.dev -> https://10.0.20.180:443` (defunct Talos Traefik VIP; caused grafana outage, then 404s for unmatched hosts after grafana fix)
- `sandhufiles.site -> https://10.0.20.180:443` (defunct site)

## Add a new-cluster hostname

1. Add tunnel ingress `{hostname, service: http://<service>.<namespace>:<port>}` above `*.rupan.dev` via dashboard or API `PUT /accounts/{id}/cfd_tunnel/{id}/configurations`. (No `HTTPRoute`/`Gateway` step: the Gateway API layer was removed; tunnel is the public edge.)
2. Confirm DNS `CNAME <host> -> <tunnel-id>.cfargotunnel.com` exists (dashboard creates it on hostname add).
3. Verify: `GET cfd_tunnel/{id}` is `healthy` with connections on `ord/mci`, `GET configurations` shows the new hostname with the in-cluster service URL in the expected position.

## Known gap

Tunnel ingress is still dashboard managed. Per ownership (`tofu/` owns API-managed systems), codify as `cloudflare_tunnel_config` under `tofu/` (only `tofu/opnsense/` exists today) to prevent drift.
