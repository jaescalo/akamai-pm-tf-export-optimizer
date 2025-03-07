module "akamai_property" {
  source = "../../modules/property"
  activate_latest_on_staging     = var.activate_latest_on_staging
  activate_latest_on_production  = var.activate_latest_on_production
  pmuser_variables               = var.pmuser_variables
  default_origin_hostname        = var.default_origin_hostname
  traffic_reporting_cp_code_id   = var.traffic_reporting_cp_code_id
  edge_hostnames                 = var.edge_hostnames
  property_config                = var.property_config
  version_notes                  = var.version_notes
  property_hostnames             = var.property_hostnames
  activation_contacts            = var.activation_contacts
}
