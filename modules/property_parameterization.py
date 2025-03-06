import re
import os
import shutil


class TerraformPropertyConverter:
    def __init__(self, property_file: str = "property.tf"):
        self.property_file = property_file
        self.variables_file = "variables.tf"
        self.tfvars_file = "terraform.tfvars"
        self.edge_hostnames = []
        self.property_params = {}
        self.version_notes = ""
        self.activation_params = {}
        self.hostnames = []
        self.property_name = ""

    def _extract_block_content(self, content: str, block_start: int) -> tuple:
        """Extract a complete block with balanced braces starting from a position."""
        open_braces = 0
        in_quotes = False
        quote_char = None
        
        for i in range(block_start, len(content)):
            char = content[i]
            
            # Handle quotes (to avoid counting braces inside strings)
            if char in ('"', "'") and (i == 0 or content[i-1] != '\\'):
                if not in_quotes:
                    in_quotes = True
                    quote_char = char
                elif char == quote_char:
                    in_quotes = False
            
            # Count braces only if not in quotes
            if not in_quotes:
                if char == '{':
                    open_braces += 1
                elif char == '}':
                    open_braces -= 1
                    if open_braces == 0:
                        return content[block_start:i+1], block_start, i+1
        
        return "", block_start, block_start  # In case of unbalanced braces

    def _kebab_to_snake(self, name: str) -> str:
        """Convert kebab-case to snake_case"""
        return name.replace('-', '_')

    def _extract_quoted_value(self, line: str) -> str:
        """Extract value within quotes from a line"""
        match = re.search(r'=\s*"([^"]+)"', line)
        if match:
            return match.group(1)
        return None

    def _extract_number_value(self, line: str) -> str:
        """Extract numeric value from a line"""
        match = re.search(r'=\s*(\d+)', line)
        if match:
            return match.group(1)
        return None

    def parse_property_file(self, input_dir) -> None:
        """
        Parse the property.tf file and extract parameters
        """
        input_property_file_path = os.path.join(input_dir, self.property_file)

        try:
            with open(input_property_file_path, 'r') as f:
                content = f.read()
        except FileNotFoundError:
            print(f"Error: File {input_property_file_path} not found")
            return
        
        # Extract edge_hostname resources
        edge_hostname_pattern = r'resource\s+"akamai_edge_hostname"\s+"([^"]+)"\s+{'
        for match in re.finditer(edge_hostname_pattern, content):
            resource_name = match.group(1)
            block_start = match.end() - 1
            block, start, end = self._extract_block_content(content, block_start)
            
            if not block:
                continue
            
            edge_hostname = {}
            edge_hostname["resource_name"] = resource_name
            
            # Extract parameters
            ip_behavior_match = re.search(r'ip_behavior\s+=\s+"([^"]+)"', block)
            if ip_behavior_match:
                edge_hostname["ip_behavior"] = ip_behavior_match.group(1)
            
            hostname_match = re.search(r'edge_hostname\s+=\s+"([^"]+)"', block)
            if hostname_match:
                edge_hostname["edge_hostname"] = hostname_match.group(1)
            
            cert_match = re.search(r'certificate\s+=\s+(\d+)', block)
            if cert_match:
                edge_hostname["certificate"] = cert_match.group(1)
            
            self.edge_hostnames.append(edge_hostname)
        
        # Extract property resource
        property_pattern = r'resource\s+"akamai_property"\s+"([^"]+)"\s+{'
        for match in re.finditer(property_pattern, content):
            property_name = match.group(1)
            self.property_name = property_name
            block_start = match.end() - 1
            block, start, end = self._extract_block_content(content, block_start)
            
            if not block:
                continue
            
            # Extract property parameters
            name_match = re.search(r'name\s+=\s+"([^"]+)"', block)
            if name_match:
                self.property_params["name"] = name_match.group(1)
            
            product_id_match = re.search(r'product_id\s+=\s+"([^"]+)"', block)
            if product_id_match:
                self.property_params["product_id"] = product_id_match.group(1)
            
            # Extract hostnames
            hostname_blocks = re.finditer(r'hostnames\s+{', block)
            for hostname_match in hostname_blocks:
                hostname_start = hostname_match.end() - 1
                hostname_block, h_start, h_end = self._extract_block_content(block, hostname_start)
                
                if not hostname_block:
                    continue
                
                hostname = {}

                cname_from_match = re.search(r'cname_from\s+=\s+"([^"]+)"', hostname_block)
                if cname_from_match:
                    hostname["cname_from"] = cname_from_match.group(1)
                
                cname_to_match = re.search(r'cname_to\s+=\s+([^\n]+)', hostname_block)

                if cname_to_match:
                    value = cname_to_match.group(1).strip()
                    # Check if this is a reference or a literal
                    if value.startswith('"') and value.endswith('"'):
                        # It's a literal string
                        hostname["cname_to"] = value.strip('"')

                    elif "akamai_edge_hostname" in value:
                        # It's a reference to an edge hostname resource
                        parts = value.split(".")
                        value = parts[1].replace("-", ".")
                        hostname["cname_to"] = value
       
                cert_type_match = re.search(r'cert_provisioning_type\s+=\s+"([^"]+)"', hostname_block)
                if cert_type_match:
                    hostname["cert_provisioning_type"] = cert_type_match.group(1)
                
                self.hostnames.append(hostname)
        
        # Extract activation resources
        activation_pattern = r'resource\s+"akamai_property_activation"\s+"([^"]+)"\s+{'
        for match in re.finditer(activation_pattern, content):
            activation_name = match.group(1)
            block_start = match.end() - 1
            block, start, end = self._extract_block_content(content, block_start)
            
            if not block:
                continue
            
            # See if we have staging or production activation
            if "staging" in activation_name.lower():
                network = "STAGING"
            elif "production" in activation_name.lower():
                network = "PRODUCTION"
            else:
                network = None
            
            if network:
                contacts = []
                contact_matches = re.findall(r'"([^"]+@[^"]+)"', block)
                contacts.extend(contact_matches)
                
                if contacts:
                    self.activation_params[f"{network.lower()}_contacts"] = contacts

    def update_variables_tf(self, output_dir) -> None:
        """
        Update variables.tf with extracted parameters
        """
        variables_file_path = os.path.join(output_dir, self.variables_file)
        existing_vars = set()
        existing_content = ""
        
        # Read existing variables if file exists
        if os.path.exists(variables_file_path):
            with open(variables_file_path, 'r') as f:
                existing_content = f.read()
                var_blocks = re.finditer(r'variable\s+"([^"]+)"\s+{', existing_content, re.DOTALL)
                for match in var_blocks:
                    var_name = match.group(1)
                    existing_vars.add(var_name)
        
        # Prepare new variable definitions
        new_vars_content = existing_content if existing_content else ""
        
        # Add edge hostname variables
        if self.edge_hostnames and "edge_hostnames" not in existing_vars:
            new_vars_content += """
# Edge Hostname Variables
variable "edge_hostnames" {
  description = "Edge hostnames configuration"
  type = map(object({
    ip_behavior   = string
    edge_hostname = string
    certificate   = number
  }))
}
"""
        
        # Add property parameters
        if self.property_params and "property_config" not in existing_vars:
            new_vars_content += """
# Property Configuration
variable "property_config" {
  description = "Property configuration parameters"
  type = object({
    name       = string
    product_id = string
  })
}
"""

        # Add property version notes
        new_vars_content += """
# Property Version Notes
variable "version_notes" {
  description = "Property version notes"
  type = string
}
"""
       
        # Add hostnames variable
        if self.hostnames and "property_hostnames" not in existing_vars:
            new_vars_content += """
# Property Hostnames
variable "property_hostnames" {
  description = "Hostnames for the property"
  type = map(object({
    cname_from             = string
    cname_to               = string
    cert_provisioning_type = string
  }))
}
"""
        
        # Add activation parameters
        if self.activation_params:
            if "activation_contacts" not in existing_vars:
                new_vars_content += """
# Activation Contacts
variable "activation_contacts" {
  description = "Contacts for property activations"
  type        = list(string)
}
"""
        
        # Write the variables file
        with open(variables_file_path, 'w') as f:
            f.write(new_vars_content)
            
        print(f"Updated {variables_file_path} with new variable definitions")

    def update_tfvars(self, output_dir) -> None:
        """
        Update terraform.tfvars with extracted values
        """
        tfvars_file_path = os.path.join(output_dir, self.tfvars_file)
        existing_content = ""
        
        # Read existing tfvars if file exists
        if os.path.exists(tfvars_file_path):
            with open(tfvars_file_path, 'r') as f:
                existing_content = f.read()
        
        new_tfvars_content = existing_content if existing_content else ""
        
        # Add edge hostname values
        if self.edge_hostnames and "edge_hostnames = {" not in existing_content:
            new_tfvars_content += "\n# Edge Hostnames\nedge_hostnames = {\n"
            for hostname in self.edge_hostnames:
                resource_name = hostname.get("resource_name", "unknown")
                new_tfvars_content += f'  "{resource_name}" = {{\n'
                
                if "ip_behavior" in hostname:
                    new_tfvars_content += f'    ip_behavior   = "{hostname["ip_behavior"]}"\n'
                else:
                    new_tfvars_content += f'    ip_behavior   = "IPV6_COMPLIANCE"\n'
                    
                if "edge_hostname" in hostname:
                    new_tfvars_content += f'    edge_hostname = "{hostname["edge_hostname"]}"\n'
                else:
                    new_tfvars_content += f'    edge_hostname = ""\n'
                    
                if "certificate" in hostname:
                    new_tfvars_content += f'    certificate   = {hostname["certificate"]}\n'
                else:
                    new_tfvars_content += f'    certificate   = 0\n'
                    
                new_tfvars_content += "  },\n"
            new_tfvars_content += "}\n"
        
        # Add property config
        if self.property_params and "property_config = {" not in existing_content:
            new_tfvars_content += "\n# Property Configuration\nproperty_config = {\n"
            if "name" in self.property_params:
                new_tfvars_content += f'  name       = "{self.property_params["name"]}"\n'
            else:
                new_tfvars_content += f'  name       = ""\n'
                
            if "product_id" in self.property_params:
                new_tfvars_content += f'  product_id = "{self.property_params["product_id"]}"\n'
            else:
                new_tfvars_content += f'  product_id = ""\n'
                
            new_tfvars_content += "}\n"
        
        # Add property version notes
        new_tfvars_content += f'version_notes = "Deployed by Terraform"\n'

        # Add hostnames
        if self.hostnames and "property_hostnames = {" not in existing_content:
            new_tfvars_content += "\n# Property Hostnames\nproperty_hostnames = {\n"
            for i, hostname in enumerate(self.hostnames):
                key = f"hostname_{i+1}"
                new_tfvars_content += f'  "{key}" = {{\n'
                
                # Handle cname_from safely
                if "cname_from" in hostname:
                    new_tfvars_content += f'    cname_from             = "{hostname["cname_from"]}"\n'
                else:
                    new_tfvars_content += f'    cname_from             = ""\n'
                
                # Handle cname_to safely                
                if "cname_to" in hostname:
                    new_tfvars_content += f'    cname_to               = "{hostname["cname_to"]}"\n'
                else:
                    new_tfvars_content += f'    cname_to               = ""\n'                
                
                # Handle cert_provisioning_type safely
                if "cert_provisioning_type" in hostname:
                    new_tfvars_content += f'    cert_provisioning_type = "{hostname["cert_provisioning_type"]}"\n'
                else:
                    new_tfvars_content += f'    cert_provisioning_type = "CPS_MANAGED"\n'
                    
                new_tfvars_content += "  },\n"
            new_tfvars_content += "}\n"
        
        # Add activation parameters
        if self.activation_params:
            # Check for contacts
            contacts = []
            for key, values in self.activation_params.items():
                if key.endswith("_contacts") and isinstance(values, list):
                    contacts.extend(values)
            
            if contacts and "activation_contacts = [" not in existing_content:
                new_tfvars_content += "\n# Activation Contacts\nactivation_contacts = [\n"
                for contact in set(contacts):  # Use set to remove duplicates
                    new_tfvars_content += f'  "{contact}",\n'
                new_tfvars_content += "]\n"
        
        # Write the tfvars file
        with open(tfvars_file_path, 'w') as f:
            f.write(new_tfvars_content)
            
        print(f"Updated {tfvars_file_path} with new variable values")

    
    def replace_in_property_file(self, input_dir, output_dir) -> None:
        """
        Replace hardcoded values in property.tf with variable references while preserving activation resources
        """
        input_property_file_path = os.path.join(input_dir, self.property_file)
        output_property_file_path = os.path.join(output_dir, self.property_file)

        # Copy the file
        shutil.copy(input_property_file_path, output_property_file_path)

        try:
            with open(output_property_file_path, 'r') as f:
                content = f.read()
        except FileNotFoundError:
            print(f"Error: File {output_property_file_path} not found")
            return
        
        # Make a backup of the original file
        backup_file = f"{output_property_file_path}.bak"
        with open(backup_file, 'w') as f:
            f.write(content)
        print(f"Created backup of {output_property_file_path} to {backup_file}")
        
        # First, remove all edge_hostname resource blocks
        updated_content = re.sub(
            r'resource\s+"akamai_edge_hostname"\s+"[^"]+"\s+{[^}]+}',
            '',
            content,
            flags=re.DOTALL
        )
        
        # Now add a single edge_hostname resource with for_each
        edge_hostname_block = """resource "akamai_edge_hostname" "edge_hostnames" {
  for_each      = var.edge_hostnames
    
  provider      = akamai
  contract_id   = var.contract_id
  group_id      = var.group_id
  ip_behavior   = each.value.ip_behavior
  edge_hostname = each.value.edge_hostname
  certificate   = each.value.certificate
}"""
    
        # Find the property resource block using a simpler pattern
        property_start_pattern = r'resource\s+"akamai_property"\s+"{0}"\s+{{'.format(re.escape(self.property_name))
        property_start_match = re.search(property_start_pattern, updated_content)
        
        if property_start_match:
            block_start = property_start_match.start()
            # Extract the entire property block
            property_block, _, block_end = self._extract_block_content(updated_content, block_start)
            
            # Prepare the property replacement
            property_replacement = f"""resource "akamai_property" "{self.property_name}" {{
  name        = var.property_config.name
  contract_id = var.contract_id
  group_id    = var.group_id
  product_id  = var.property_config.product_id

  dynamic "hostnames" {{
    for_each = var.property_hostnames
    content {{
      cname_from             = hostnames.value.cname_from
      cname_to               = hostnames.value.cname_to
      cert_provisioning_type = hostnames.value.cert_provisioning_type
    }}
  }}
  rule_format   = data.akamai_property_rules_builder.{self.property_name}_rule_default.rule_format
  rules         = data.akamai_property_rules_builder.{self.property_name}_rule_default.json
  version_notes = var.version_notes
}}"""
        
            # Replace the entire property block
            updated_content = updated_content[:block_start] + property_replacement + updated_content[block_end:]
        
        # Remove any separate akamai_property_hostname resources
        updated_content = re.sub(
            r'resource\s+"akamai_property_hostname"\s+"[^"]+"\s+{[^}]+}',
            '',
            updated_content,
            flags=re.DOTALL
        )
        
        # Clean up any potential extra spaces or newlines
        updated_content = re.sub(r'\n{3,}', '\n\n', updated_content)
        
        # Insert the edge_hostname block after terraform/provider blocks but before property blocks
        provider_match = re.search(r'provider\s+"akamai"\s+{[^}]+}', updated_content, re.DOTALL)
        if provider_match:
            insert_position = provider_match.end()
            updated_content = updated_content[:insert_position] + "\n\n" + edge_hostname_block + updated_content[insert_position:]
        else:
            # If provider block not found, just insert at the beginning
            updated_content = edge_hostname_block + updated_content
        
        # Better approach for removing activation resources: split and rebuild the file
        # Find the last closing bracket of the property resource
        last_property_position = updated_content.find(f'resource "akamai_property" "{self.property_name}"')
        if last_property_position != -1:
            # Find the closing brace of the property resource
            property_block_start = last_property_position
            property_block, _, property_block_end = self._extract_block_content(updated_content, property_block_start)
            
            # Keep everything up to the end of the property resource
            base_content = updated_content[:property_block_end]
            
            # Remove any trailing whitespace
            base_content = base_content.rstrip()
            
            # Create new activation resources
            staging_activation = f"""resource "akamai_property_activation" "{self.property_name}-staging" {{
  property_id                    = akamai_property.{self.property_name}.id
  contact                        = var.activation_contacts
  version                        = var.activate_latest_on_staging ? akamai_property.{self.property_name}.latest_version : akamai_property.{self.property_name}.staging_version
  network                        = "STAGING"
  note                           = var.version_notes
  auto_acknowledge_rule_warnings = "true"
}}"""
        
            production_activation = f"""resource "akamai_property_activation" "{self.property_name}-production" {{
  property_id                    = akamai_property.{self.property_name}.id
  contact                        = var.activation_contacts
  version                        = var.activate_latest_on_production ? akamai_property.{self.property_name}.latest_version : akamai_property.{self.property_name}.production_version
  network                        = "PRODUCTION"
  note                           = var.version_notes
  auto_acknowledge_rule_warnings = "true"
}}"""
        
            # Rebuild the file with only the content we want
            updated_content = base_content + "\n\n" + staging_activation + "\n\n" + production_activation
        
        # Clean up any potential extra spaces or newlines
        updated_content = re.sub(r'\n{3,}', '\n\n', updated_content)
        
        # Write the updated content back
        with open(output_property_file_path, 'w') as f:
            f.write(updated_content)
            
        print(f"Updated {output_property_file_path} with variable references, dynamic hostnames block, and activation resources")

def parameterize_property_resources(input_dir, output_dir):
    converter = TerraformPropertyConverter(property_file="property.tf")
    converter.parse_property_file(input_dir)
    
    print("\nExtracted Edge Hostnames:")
    for hostname in converter.edge_hostnames:
        print(f"  {hostname}")
    
    print("\nExtracted Property Parameters:")
    for key, value in converter.property_params.items():
        print(f"  {key}: {value}")
    
    print("\nExtracted Hostnames:")
    for hostname in converter.hostnames:
        print(f"  {hostname}")
    
    print("\nExtracted Activation Parameters:")
    for key, value in converter.activation_params.items():
        print(f"  {key}: {value}")
    
    # Update files
    converter.update_variables_tf(output_dir)
    converter.update_tfvars(output_dir)
    converter.replace_in_property_file(input_dir, output_dir)

if __name__ == "__main__":
    parameterize_property_resources(input_dir="../test", output_dir="../result")