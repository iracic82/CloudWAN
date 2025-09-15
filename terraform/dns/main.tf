# -----------------------------
# Look up Default DNS View
# -----------------------------
data "bloxone_dns_views" "default_view" {
  filters = {
    name = "default"
  }
}

# -----------------------------
# Look up Existing Zone
# -----------------------------
data "bloxone_dns_auth_zones" "infolab_zone" {
  filters = {
    fqdn = var.zone_fqdn
    view = data.bloxone_dns_views.default_view.results[0].id
  }
}

# -----------------------------
# Create A Records
# -----------------------------
resource "bloxone_dns_a_record" "app1" {
  rdata = {
    address = var.app1_ip
  }
  zone          = data.bloxone_dns_auth_zones.infolab_zone.results[0].id
  name_in_zone  = "app1"
  ttl           = 300
  comment       = "App1 Prod record"
}

resource "bloxone_dns_a_record" "app2" {
  rdata = {
    address = var.app2_ip
  }
  zone          = data.bloxone_dns_auth_zones.infolab_zone.results[0].id
  name_in_zone  = "app2"
  ttl           = 300
  comment       = "App2 Prod record"
}
