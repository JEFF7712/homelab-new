vlans = {
  management = {
    description = "management"
    device      = "vlan10"
    parent      = "igb0"
    tag         = 10
  }
  clients = {
    description = "clients"
    device      = "vlan20"
    parent      = "igb0"
    tag         = 20
  }
  infrastructure = {
    description = "infrastructure"
    device      = "vlan30"
    parent      = "igb0"
    tag         = 30
  }
  load-balancers = {
    description = "load-balancers"
    device      = "vlan40"
    parent      = "igb0"
    tag         = 40
  }
  guest-iot = {
    description = "guest-iot"
    device      = "vlan50"
    parent      = "igb0"
    tag         = 50
  }
  netbird = {
    description = "netbird"
    device      = "vlan60"
    parent      = "igb0"
    tag         = 60
  }
}

dhcpv4_subnets = {
  management = {
    description = "management"
    dns_servers = ["10.0.10.1"]
    pools       = ["10.0.10.100-10.0.10.199"]
    routers     = ["10.0.10.1"]
    subnet      = "10.0.10.0/24"
  }
  clients = {
    description = "clients"
    dns_servers = ["10.0.20.1"]
    pools       = ["10.0.20.100-10.0.20.249"]
    routers     = ["10.0.20.1"]
    subnet      = "10.0.20.0/24"
  }
  infrastructure = {
    description = "infrastructure"
    dns_servers = ["10.0.30.1"]
    pools       = ["10.0.30.100-10.0.30.199"]
    routers     = ["10.0.30.1"]
    subnet      = "10.0.30.0/24"
  }
  guest-iot = {
    description = "guest-iot"
    dns_servers = ["10.0.50.1"]
    pools       = ["10.0.50.100-10.0.50.249"]
    routers     = ["10.0.50.1"]
    subnet      = "10.0.50.0/24"
  }
}
