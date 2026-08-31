# k3s + Cilium control plane findings

Research date: 2026-08-30. Scope: a greenfield k3s cluster, Cilium CNI,
kube-proxy replacement, and BGP peering to OPNsense. The selected Cilium
release must be pinned before implementation; the linked stable documentation
currently shows 1.20.1 for the k3s installation instructions.

## Supported k3s and Cilium bootstrap inputs

- Install k3s with its default CNI disabled using `--flannel-backend=none`.
  K3s recommends also passing `--disable-network-policy` when a custom CNI
  supplies its own network-policy implementation. K3s says the Flannel options
  on server nodes must be identical across all servers.
- The Cilium k3s installation page gives the same two k3s options, then installs
  Cilium after the Kubernetes API is available. It identifies the admin
  kubeconfig as `/etc/rancher/k3s/k3s.yaml`.
- Cilium's Helm value `kubeProxyReplacement=true` is the supported full
  replacement switch. With it enabled, configure `k8sServiceHost` and
  `k8sServicePort` to a Kubernetes API endpoint reachable directly by every
  Cilium agent. Cilium documents those two settings as required for
  kube-proxy-replacement operation, including after kube-proxy removal.
- The exact k3s release configuration for suppressing its packaged kube-proxy
  must be verified against the pinned k3s release before implementation. Do
  not treat merely enabling Cilium's replacement as proof that k3s kube-proxy
  is absent.

Sources:

- https://docs.k3s.io/networking/basic-network-options
- https://docs.cilium.io/en/stable/installation/k8s-install-helm/
- https://docs.cilium.io/en/stable/network/kubernetes/kubeproxy-free/
- https://docs.cilium.io/en/stable/helm-values/

## BGP control plane contract

- Use Cilium BGP Control Plane v2 resources: `CiliumBGPClusterConfig`,
  `CiliumBGPPeerConfig`, `CiliumBGPAdvertisement`, and, only if needed,
  `CiliumBGPNodeConfigOverride`. The former BGPv1 `CiliumBGPPeeringPolicy`
  has been removed.
- `CiliumBGPClusterConfig` selects nodes and defines each instance's local ASN
  plus peer address/ASN. A node must match at most one cluster configuration;
  conflicting selectors are rejected. Therefore, label the intended control
  plane and worker nodes before applying the cluster config, and use one
  cluster config for the OPNsense peer.
- `CiliumBGPPeerConfig` supplies IPv4-unicast address-family configuration and
  an advertisement selector. With no matching `CiliumBGPAdvertisement`, Cilium
  advertises no prefixes. This is a useful default-deny property.
- By default Cilium initiates BGP sessions but does not listen. The OPNsense
  FRR peer should therefore accept sessions initiated by each selected node.
  Setting `localPort: 179` makes Cilium listen, but requires
  `CAP_NET_BIND_SERVICE` for the Cilium agent. Prefer Cilium's default active
  initiation unless OPNsense needs the reverse direction.
- Cilium chooses the BGP source address through a route lookup to the peer;
  `localAddress` can pin it per peer when a node has multiple links. For the
  planned VLAN design, peer OPNsense at its VLAN 30 address and ensure node
  management addresses are stable, routable, and permitted to reach TCP/179.
- On IPv4 or dual-stack nodes, the default router ID is the node IPv4 address.
  A per-node override or an explicitly configured IP pool is available if that
  is unsuitable.

Sources:

- https://docs.cilium.io/en/stable/network/bgp-control-plane/bgp-control-plane-configuration/
- https://docs.cilium.io/en/stable/network/bgp-control-plane/bgp-control-plane-troubleshooting/
- https://docs.cilium.io/en/stable/operations/upgrade/

## LoadBalancer address advertisement

- Define a `CiliumLoadBalancerIPPool` from a deliberately reserved portion of
  VLAN 40. Cilium LB IPAM allocates `type: LoadBalancer` Service addresses but
  does not itself advertise or load-balance them.
- Select BGP delivery with `loadBalancerClass:
  io.cilium/bgp-control-plane` on each intended LoadBalancer Service. A
  `CiliumBGPAdvertisement` matching the peer configuration must select
  `Service` and `LoadBalancerIP`; Cilium advertises Service VIPs as exact
  `/32` IPv4 routes.
- Changing an IP pool can reassign Service addresses. Treat the pool range as
  an immutable network contract after services receive addresses.

Source:

- https://docs.cilium.io/en/stable/network/lb-ipam/

## Validated bootstrap order

1. In OpenTofu-managed OPNsense, create VLAN 30 for cluster nodes and reserve a
   non-DHCP portion of VLAN 40 for Kubernetes LoadBalancer addresses. Configure
   FRR with the selected cluster ASN and one neighbor for each expected node
   address. Permit BGP TCP/179 from the selected nodes to OPNsense.
2. Install the first k3s server with `--flannel-backend=none` and
   `--disable-network-policy`; apply the same server-side Flannel setting to
   every additional server. Do not deploy normal workloads before Cilium is
   healthy.
3. Install a pinned Cilium chart from its OCI registry. Set a directly reachable
   API endpoint using `k8sServiceHost` and `k8sServicePort`, and enable
   `kubeProxyReplacement=true`. Verify the Cilium agents and operator are
   ready before joining workload nodes.
4. Join and label the remaining nodes, then apply the v2 BGP peer configuration
   and confirm that a generated `CiliumBGPNodeConfig` exists for every selected
   node and each BGP session is established.
5. Apply the VLAN 40 LB IP pool and narrowly labelled BGP advertisements. Test
   with one labelled LoadBalancer Service, verify that OPNsense learns its /32
   route, then make the address pool available to platform ingress services.

The documented checks to use during step 4 are: inspect generated
`CiliumBGPNodeConfig` resources, inspect cluster-config status for selector or
peer-reference errors, and inspect Cilium operator logs if those resources are
not created.
