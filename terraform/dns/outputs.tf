output "dns_records" {
  description = "Created DNS records"
  value = {
    app1 = "${bloxone_dns_a_record.app1.name_in_zone}.${var.zone_fqdn} -> ${var.app1_ip}"
    app2 = "${bloxone_dns_a_record.app2.name_in_zone}.${var.zone_fqdn} -> ${var.app2_ip}"
  }
}
