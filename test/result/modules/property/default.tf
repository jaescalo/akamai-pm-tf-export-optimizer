data "akamai_property_rules_builder" "tf-demo-com_rule_default" {
  rules_v2025_01_13 {
    name      = "default"
    is_secure = true
    comments  = "The Default Rule template contains all the necessary and recommended behaviors. Rules are evaluated from top to bottom and the last matching rule wins."
    dynamic "variable" {
      for_each = var.pmuser_variables
      content {
        name        = "PMUSER_${upper(variable.key)}"
        description = variable.value.description
        value       = variable.value.value
        hidden      = variable.value.hidden
        sensitive   = variable.value.sensitive
      }
    }
    behavior {
      origin {
        cache_key_hostname            = "REQUEST_HOST_HEADER"
        compress                      = true
        enable_true_client_ip         = true
        forward_host_header           = "REQUEST_HOST_HEADER"
        hostname                      = var.default_origin_hostname
        http_port                     = 80
        https_port                    = 443
        ip_version                    = "IPV4"
        min_tls_version               = "DYNAMIC"
        origin_certificate            = ""
        origin_sni                    = true
        origin_type                   = "CUSTOMER"
        ports                         = ""
        tls_version_title             = ""
        true_client_ip_client_setting = false
        true_client_ip_header         = "True-Client-IP"
        verification_mode             = "PLATFORM_SETTINGS"
      }
    }
    children = [
      data.akamai_property_rules_builder.tf-demo-com_rule_augment_insights.json,
      data.akamai_property_rules_builder.tf-demo-com_rule_accelerate_delivery.json,
      data.akamai_property_rules_builder.tf-demo-com_rule_offload_origin.json,
      data.akamai_property_rules_builder.tf-demo-com_rule_strengthen_security.json,
      data.akamai_property_rules_builder.tf-demo-com_rule_increase_availability.json,
      data.akamai_property_rules_builder.tf-demo-com_rule_minimize_payload.json,
    ]
  }
}