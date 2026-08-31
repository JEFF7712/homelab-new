resource "opnsense_interfaces_vlan" "managed" {
  for_each = var.vlans

  description = each.value.description
  parent      = each.value.parent
  tag         = each.value.tag

  lifecycle {
    ignore_changes = [device]
  }
}

resource "opnsense_kea_dhcpv4_subnet" "managed" {
  for_each = var.dhcpv4_subnets

  auto_collect = false
  description  = each.value.description
  dns_servers  = each.value.dns_servers
  pools        = each.value.pools
  routers      = each.value.routers
  subnet       = each.value.subnet
}

resource "opnsense_kea_dhcpv4_reservation" "managed" {
  for_each = var.dhcpv4_reservations

  description = each.value.description
  hostname    = each.value.hostname
  ip_address  = each.value.ip_address
  mac_address = each.value.mac_address
  subnet_id   = each.value.subnet_id
}

resource "opnsense_firewall_filter" "managed" {
  for_each = var.firewall_filters

  description = each.value.description
  enabled     = each.value.enabled
  filter      = each.value.filter
  interface   = each.value.interface
  sequence    = each.value.sequence
}

resource "opnsense_unbound_settings" "managed" {
  count = var.manage_unbound ? 1 : 0

  acls       = try(var.unbound_settings.acls, null)
  advanced   = try(var.unbound_settings.advanced, null)
  forwarding = try(var.unbound_settings.forwarding, null)
  general    = try(var.unbound_settings.general, null)
}

resource "opnsense_unbound_forward" "managed" {
  for_each = var.unbound_forwards

  domain      = each.value.domain
  enabled     = each.value.enabled
  server_ip   = each.value.server_ip
  server_port = each.value.server_port
  type        = each.value.type
  verify_cn   = each.value.verify_cn
}
