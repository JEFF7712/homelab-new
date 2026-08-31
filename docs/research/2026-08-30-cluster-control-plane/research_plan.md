# Cluster Control Plane Research Plan

## Main question

What current, supported integration pattern should the greenfield homelab use for a k3s cluster with Cilium BGP, Flux GitOps, and OPNsense managed by OpenTofu?

## Subtopics

1. k3s and Cilium: supported kube-proxy replacement, CNI disablement, installation ordering, and Cilium BGP control-plane requirements.
2. Flux bootstrap and secrets: supported bootstrap layout, reconciliation, pruning, and External Secrets patterns for GitLab-backed Kubernetes secrets.
3. OPNsense declarative management: current OpenTofu provider capabilities and constraints for VLANs, DHCP, firewall policy, DNS, and BGP peer configuration.

## Synthesis

Use only primary documentation where possible. Translate verified constraints into a cluster architecture section with explicit bootstrap order, ownership boundaries, and validation gates. Flag capabilities that require manual import, are experimental, or cannot be managed declaratively.
