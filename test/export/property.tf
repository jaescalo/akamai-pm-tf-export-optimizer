terraform {
  required_providers {
    akamai = {
      source  = "akamai/akamai"
      version = ">= 7.0.0"
    }
  }
  required_version = ">= 1.0"
}

provider "akamai" {
  edgerc         = var.edgerc_path
  config_section = var.config_section
}

resource "akamai_edge_hostname" "tf-demo-com-edgesuite-net" {
  contract_id   = var.contract_id
  group_id      = var.group_id
  ip_behavior   = "IPV6_COMPLIANCE"
  edge_hostname = "tf-demo.com.edgesuite.net"
}

resource "akamai_property" "tf-demo-com" {
  name        = "tf-demo.com"
  contract_id = var.contract_id
  group_id    = var.group_id
  product_id  = "prd_Fresca"
  hostnames {
    cname_from             = "tf-demo.com"
    cname_to               = akamai_edge_hostname.tf-demo-com-edgesuite-net.edge_hostname
    cert_provisioning_type = "DEFAULT"
  }
  hostnames {
    cname_from             = "www.tf-demo.com"
    cname_to               = akamai_edge_hostname.tf-demo-com-edgesuite-net.edge_hostname
    cert_provisioning_type = "DEFAULT"
  }
  rule_format = data.akamai_property_rules_builder.tf-demo-com_rule_default.rule_format
  rules       = data.akamai_property_rules_builder.tf-demo-com_rule_default.json
}

# NOTE: Be careful when removing this resource as you can disable traffic
resource "akamai_property_activation" "tf-demo-com-staging" {
  property_id                    = akamai_property.tf-demo-com.id
  contact                        = ["noreply@akamai.com"]
  version                        = var.activate_latest_on_staging ? akamai_property.tf-demo-com.latest_version : akamai_property.tf-demo-com.staging_version
  network                        = "STAGING"
  note                           = "Initial version"
  auto_acknowledge_rule_warnings = false
}

# NOTE: Be careful when removing this resource as you can disable traffic
resource "akamai_property_activation" "tf-demo-com-production" {
  property_id                    = akamai_property.tf-demo-com.id
  contact                        = ["noreply@akamai.com"]
  version                        = var.activate_latest_on_production ? akamai_property.tf-demo-com.latest_version : akamai_property.tf-demo-com.production_version
  network                        = "PRODUCTION"
  note                           = "Initial version"
  auto_acknowledge_rule_warnings = false
}
