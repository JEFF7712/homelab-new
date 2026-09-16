variable "opnsense_uri" {
  type        = string
  description = "OPNsense API base URL. Credentials are supplied through protected environment variables."
}

variable "vlans" {
  type = map(object({
    description = string
    parent      = string
    tag         = number
  }))
  default = {}
}

variable "dhcpv4_subnets" {
  type = map(object({
    description = string
    dns_servers = set(string)
    pools       = set(string)
    routers     = set(string)
    subnet      = string
  }))
  default = {}
}

variable "dhcpv4_reservations" {
  type = map(object({
    description = string
    hostname    = string
    ip_address  = string
    mac_address = string
    subnet_id   = string
  }))
  default = {}
}

variable "firewall_aliases" {
  type = map(object({
    name        = string
    type        = string
    content     = set(string)
    description = string
    enabled     = bool
  }))
  default = {}
}

variable "firewall_filters" {
  type = map(object({
    description = string
    enabled     = bool
    sequence    = number
    interface = object({
      interface = list(string)
    })
    filter = object({
      action      = string
      direction   = string
      ip_protocol = string
      protocol    = string
      quick       = bool
      log         = bool
      source = object({
        net  = string
        port = string
      })
      destination = object({
        net  = string
        port = string
      })
    })
  }))
  default = {}
}

variable "manage_unbound" {
  type    = bool
  default = false
}

variable "unbound_settings" {
  type    = any
  default = {}
}

variable "unbound_forwards" {
  type = map(object({
    domain      = string
    enabled     = bool
    server_ip   = string
    server_port = number
    type        = string
    verify_cn   = string
  }))
  default = {}
}
