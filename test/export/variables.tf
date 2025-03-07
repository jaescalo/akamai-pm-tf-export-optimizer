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
