variable "edgerc_path" {
  type    = string
  default = "~/.edgerc"
}

variable "config_section" {
  type    = string
  default = "tf"
}

variable "contract_id" {
  type    = string
  default = "ctr_1-1NC95D"
}

variable "group_id" {
  type    = string
  default = "grp_257477"
}

variable "activate_latest_on_staging" {
  type    = bool
  default = false
}

variable "activate_latest_on_production" {
  type    = bool
  default = false
}

# PMUSER variables
variable "pmuser_variables" {
  description = "Map of PMUSER variables with their descriptions and sensitivity settings"
  type = map(object({
    description = string
    value       = string
    hidden      = bool
    sensitive   = bool
  }))
}

variable "default_origin_hostname" {
  description = "Extracted from Terraform rules file"
  type        = string
}

variable "traffic_reporting_cp_code_id" {
  description = "Extracted from Terraform rules file"
  type        = number
}

# Edge Hostname Variables
variable "edge_hostnames" {
  description = "Edge hostnames configuration"
  type = map(object({
    ip_behavior   = string
    edge_hostname = string
    certificate   = number
  }))
}

# Property Configuration
variable "property_config" {
  description = "Property configuration parameters"
  type = object({
    name       = string
    product_id = string
  })
}

# Property Version Notes
variable "version_notes" {
  description = "Property version notes"
  type = string
}

# Property Hostnames
variable "property_hostnames" {
  description = "Hostnames for the property"
  type = map(object({
    cname_from             = string
    cname_to               = string
    cert_provisioning_type = string
  }))
}

# Activation Contacts
variable "activation_contacts" {
  description = "Contacts for property activations"
  type        = list(string)
}
