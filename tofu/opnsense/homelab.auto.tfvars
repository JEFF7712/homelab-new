vlans = {
  management = {
    description = "management"
    parent      = "igb0"
    tag         = 10
  }
  clients = {
    description = "clients"
    parent      = "igb0"
    tag         = 20
  }
  infrastructure = {
    description = "infrastructure"
    parent      = "igb0"
    tag         = 30
  }
  load-balancers = {
    description = "load-balancers"
    parent      = "igb0"
    tag         = 40
  }
  guest-iot = {
    description = "guest-iot"
    parent      = "igb0"
    tag         = 50
  }
  netbird = {
    description = "netbird"
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
    dns_servers = ["10.0.30.10"]
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

firewall_filters = {
  management-allow-any = {
    description = "Allow management VLAN to all destinations"
    enabled     = true
    sequence    = 100
    interface   = { interface = ["opt2"] }
    filter = {
      action      = "pass"
      direction   = "in"
      ip_protocol = "inet"
      protocol    = "any"
      quick       = true
      log         = false
      source      = { net = "10.0.10.0/24", port = "" }
      destination = { net = "any", port = "" }
    }
  }
  clients-allow-dns = {
    description = "Allow clients to OPNsense DNS"
    enabled     = true
    sequence    = 200
    interface   = { interface = ["opt1"] }
    filter = {
      action      = "pass"
      direction   = "in"
      ip_protocol = "inet"
      protocol    = "TCP/UDP"
      quick       = true
      log         = false
      source      = { net = "10.0.20.0/24", port = "" }
      destination = { net = "10.0.20.1", port = "53" }
    }
  }
  clients-allow-load-balancers = {
    description = "Allow clients to Kubernetes services"
    enabled     = true
    sequence    = 210
    interface   = { interface = ["opt1"] }
    filter = {
      action      = "pass"
      direction   = "in"
      ip_protocol = "inet"
      protocol    = "any"
      quick       = true
      log         = false
      source      = { net = "10.0.20.0/24", port = "" }
      destination = { net = "10.0.40.0/24", port = "" }
    }
  }
  clients-block-private = {
    description = "Block clients from other private VLANs"
    enabled     = true
    sequence    = 220
    interface   = { interface = ["opt1"] }
    filter = {
      action      = "block"
      direction   = "in"
      ip_protocol = "inet"
      protocol    = "any"
      quick       = true
      log         = true
      source      = { net = "10.0.20.0/24", port = "" }
      destination = { net = "10.0.0.0/8", port = "" }
    }
  }
  clients-allow-internet = {
    description = "Allow clients to the Internet"
    enabled     = true
    sequence    = 230
    interface   = { interface = ["opt1"] }
    filter = {
      action      = "pass"
      direction   = "in"
      ip_protocol = "inet"
      protocol    = "any"
      quick       = true
      log         = false
      source      = { net = "10.0.20.0/24", port = "" }
      destination = { net = "any", port = "" }
    }
  }
  infrastructure-allow-dns = {
    description = "Allow infrastructure to OPNsense DNS"
    enabled     = true
    sequence    = 300
    interface   = { interface = ["opt3"] }
    filter = {
      action      = "pass"
      direction   = "in"
      ip_protocol = "inet"
      protocol    = "TCP/UDP"
      quick       = true
      log         = false
      source      = { net = "10.0.30.0/24", port = "" }
      destination = { net = "10.0.30.1", port = "53" }
    }
  }
  infrastructure-allow-opnsense-api = {
    description = "Allow the private runner to reach the OPNsense API"
    enabled     = true
    sequence    = 305
    interface   = { interface = ["opt3"] }
    filter = {
      action      = "pass"
      direction   = "in"
      ip_protocol = "inet"
      protocol    = "TCP"
      quick       = true
      log         = false
      source      = { net = "10.0.30.0/24", port = "" }
      destination = { net = "10.0.10.1", port = "443" }
    }
  }
  infrastructure-allow-load-balancers = {
    description = "Allow infrastructure to Kubernetes service VIPs"
    enabled     = true
    sequence    = 310
    interface   = { interface = ["opt3"] }
    filter = {
      action      = "pass"
      direction   = "in"
      ip_protocol = "inet"
      protocol    = "any"
      quick       = true
      log         = false
      source      = { net = "10.0.30.0/24", port = "" }
      destination = { net = "10.0.40.0/24", port = "" }
    }
  }
  infrastructure-block-private = {
    description = "Block infrastructure from initiating to other private VLANs"
    enabled     = true
    sequence    = 320
    interface   = { interface = ["opt3"] }
    filter = {
      action      = "block"
      direction   = "in"
      ip_protocol = "inet"
      protocol    = "any"
      quick       = true
      log         = true
      source      = { net = "10.0.30.0/24", port = "" }
      destination = { net = "10.0.0.0/8", port = "" }
    }
  }
  infrastructure-allow-internet = {
    description = "Allow infrastructure to the Internet"
    enabled     = true
    sequence    = 330
    interface   = { interface = ["opt3"] }
    filter = {
      action      = "pass"
      direction   = "in"
      ip_protocol = "inet"
      protocol    = "any"
      quick       = true
      log         = false
      source      = { net = "10.0.30.0/24", port = "" }
      destination = { net = "any", port = "" }
    }
  }
  load-balancers-allow-any = {
    description = "Allow Kubernetes service VIP traffic"
    enabled     = true
    sequence    = 400
    interface   = { interface = ["opt4"] }
    filter = {
      action      = "pass"
      direction   = "in"
      ip_protocol = "inet"
      protocol    = "any"
      quick       = true
      log         = false
      source      = { net = "10.0.40.0/24", port = "" }
      destination = { net = "any", port = "" }
    }
  }
  guest-iot-allow-dns = {
    description = "Allow guest and IoT devices to OPNsense DNS"
    enabled     = true
    sequence    = 500
    interface   = { interface = ["opt5"] }
    filter = {
      action      = "pass"
      direction   = "in"
      ip_protocol = "inet"
      protocol    = "TCP/UDP"
      quick       = true
      log         = false
      source      = { net = "10.0.50.0/24", port = "" }
      destination = { net = "10.0.50.1", port = "53" }
    }
  }
  guest-iot-block-private = {
    description = "Block guest and IoT devices from private VLANs"
    enabled     = true
    sequence    = 510
    interface   = { interface = ["opt5"] }
    filter = {
      action      = "block"
      direction   = "in"
      ip_protocol = "inet"
      protocol    = "any"
      quick       = true
      log         = true
      source      = { net = "10.0.50.0/24", port = "" }
      destination = { net = "10.0.0.0/8", port = "" }
    }
  }
  guest-iot-allow-internet = {
    description = "Allow guest and IoT devices to the Internet"
    enabled     = true
    sequence    = 520
    interface   = { interface = ["opt5"] }
    filter = {
      action      = "pass"
      direction   = "in"
      ip_protocol = "inet"
      protocol    = "any"
      quick       = true
      log         = false
      source      = { net = "10.0.50.0/24", port = "" }
      destination = { net = "any", port = "" }
    }
  }
  netbird-allow-private = {
    description = "Allow NetBird policy segment to homelab VLANs"
    enabled     = true
    sequence    = 600
    interface   = { interface = ["opt6"] }
    filter = {
      action      = "pass"
      direction   = "in"
      ip_protocol = "inet"
      protocol    = "any"
      quick       = true
      log         = false
      source      = { net = "10.0.60.0/24", port = "" }
      destination = { net = "10.0.0.0/8", port = "" }
    }
  }
}
