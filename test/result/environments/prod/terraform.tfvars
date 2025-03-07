
activate_latest_on_staging = false
activate_latest_on_production = false


pmuser_variables = {
  "A_TEST" = {
    description = "A/B Testing"
    value       = "a_home.html"
    hidden      = false
    sensitive   = false
  },
  "B_TEST" = {
    description = "A/B Testing"
    value       = "b_home.html"
    hidden      = false
    sensitive   = false
  },
}
default_origin_hostname = "origin.tf-demo.com"
traffic_reporting_cp_code_id = 1662022

# Edge Hostnames
edge_hostnames = {
  "tf-demo-com-edgesuite-net" = {
    ip_behavior   = "IPV6_COMPLIANCE"
    edge_hostname = "tf-demo.com.edgesuite.net"
    certificate   = 0
  },
}

# Property Configuration
property_config = {
  name       = "tf-demo.com"
  product_id = "prd_Fresca"
}
version_notes = "Deployed by Terraform"

# Property Hostnames
property_hostnames = {
  "hostname_1" = {
    cname_from             = "tf-demo.com"
    cname_to               = "tf.demo.com.edgesuite.net"
    cert_provisioning_type = "DEFAULT"
  },
  "hostname_2" = {
    cname_from             = "www.tf-demo.com"
    cname_to               = "tf.demo.com.edgesuite.net"
    cert_provisioning_type = "DEFAULT"
  },
}

# Activation Contacts
activation_contacts = [
  "noreply@akamai.com",
]
