# OPNsense BGP Proof

Run after an FRR configuration apply and before migrating application traffic.

1. Confirm FRR service status is running.
2. Confirm every Cilium peer is established with the expected ASN.
3. Confirm the canary Cilium LoadBalancer `/32` is present in the IPv4 BGP RIB.
4. Retain redacted proof output with the pipeline artifact.

An absent peer, wrong ASN, missing route, or non-running service is an apply failure. Restore connectivity using the OPNsense console recovery runbook before attempting another configuration change.
