terraform init
terraform import akamai_edge_hostname.tf-demo-com-edgesuite-net ehn_5655851,ctr_1-1NC95D,grp_257477
terraform import akamai_property.tf-demo-com prp_1072446,ctr_1-1NC95D,grp_257477,3
terraform import akamai_property_activation.tf-demo-com-staging prp_1072446:STAGING
terraform import akamai_property_activation.tf-demo-com-production prp_1072446:PRODUCTION
