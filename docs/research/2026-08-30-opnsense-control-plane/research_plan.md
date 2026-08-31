# OPNsense Control Plane Research Plan

## Main question

What exact API and OpenTofu operations are required to declaratively reconcile
the approved OPNsense VLAN, DHCP, firewall, DNS, and Cilium BGP design?

## Subtopics

1. OPNsense core API endpoints and backup mechanism for interface assignment,
   interface IPv4 settings, and configuration export.
2. FRR API endpoints and verification operations for global BGP configuration,
   neighbors, and learned routes.
3. OpenTofu provider imports and resources for VLAN devices, Kea DHCP, Unbound,
   and firewall policy.

## Synthesis

Produce a safe implementation plan that separates read-only inventory, backup,
import, dry-run validation, and explicitly authorized apply operations.
