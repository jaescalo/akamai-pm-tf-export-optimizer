resource "akamai_edge_hostname" "edge_hostnames" {
  for_each      = var.edge_hostnames
    
  provider      = akamai
  contract_id   = var.contract_id
  group_id      = var.group_id
  ip_behavior   = each.value.ip_behavior
  edge_hostname = each.value.edge_hostname
  certificate   = each.value.certificate
}

resource "akamai_property" "tf-demo-com" {
  name        = var.property_config.name
  contract_id = var.contract_id
  group_id    = var.group_id
  product_id  = var.property_config.product_id

  dynamic "hostnames" {
    for_each = var.property_hostnames
    content {
      cname_from             = hostnames.value.cname_from
      cname_to               = hostnames.value.cname_to
      cert_provisioning_type = hostnames.value.cert_provisioning_type
    }
  }
  rule_format   = data.akamai_property_rules_builder.tf-demo-com_rule_default.rule_format
  rules         = data.akamai_property_rules_builder.tf-demo-com_rule_default.json
  version_notes = var.version_notes
}

resource "akamai_property_activation" "tf-demo-com-staging" {
  property_id                    = akamai_property.tf-demo-com.id
  contact                        = var.activation_contacts
  version                        = var.activate_latest_on_staging ? akamai_property.tf-demo-com.latest_version : akamai_property.tf-demo-com.staging_version
  network                        = "STAGING"
  note                           = var.version_notes
  auto_acknowledge_rule_warnings = "true"
}

resource "akamai_property_activation" "tf-demo-com-production" {
  property_id                    = akamai_property.tf-demo-com.id
  contact                        = var.activation_contacts
  version                        = var.activate_latest_on_production ? akamai_property.tf-demo-com.latest_version : akamai_property.tf-demo-com.production_version
  network                        = "PRODUCTION"
  note                           = var.version_notes
  auto_acknowledge_rule_warnings = "true"
}