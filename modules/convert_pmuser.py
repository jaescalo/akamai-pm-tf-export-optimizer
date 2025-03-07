import re
import os
import shutil
from typing import Dict, List, Any


class TerraformPropertyVariablesConverter:
    def __init__(self, rules_file: str = "rules.tf"):
        self.rules_file = rules_file
        self.variables_file = "variables.tf"
        self.tfvars_file = "terraform.tfvars"
        self.extracted_pmuser_vars = {}
        self.variable_blocks_positions = []  # To track the positions of variable blocks

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

    def parse_rules_file(self, input_dir) -> Dict[str, Dict[str, Any]]:
        """
        Parse the rules.tf file and extract PMUSER variable blocks from the default rule
        """
        input_rules_file_path = os.path.join(input_dir, self.rules_file)

        try:
            with open(input_rules_file_path, 'r') as f:
                content = f.read()
        except FileNotFoundError:
            print(f"Error: File {input_rules_file_path} not found")
            return {}
        
        results = {}
        
        # Find the data block for the default rule
        # This pattern looks for a data block with a name ending with "_rule_default"
        data_block_pattern = r'data\s+"akamai_property_rules_builder"\s+"([^"]+_rule_default)"\s+{'
        for match in re.finditer(data_block_pattern, content):
            data_name = match.group(1)
            block_start = match.end() - 1  # Position of the opening brace
            
            # Extract the complete data block
            data_block, data_start, data_end = self._extract_block_content(content, block_start)
            if not data_block:
                continue
                
            # Find all variable blocks within this data block
            var_pattern = r'variable\s+{'
            var_block_positions = []  # List to store the start and end positions of all variable blocks
            
            for var_match in re.finditer(var_pattern, data_block):
                var_start = var_match.end() - 1 + data_start  # Position of opening brace
                var_block, var_block_start, var_block_end = self._extract_block_content(content, var_start)
                
                if not var_block:
                    continue
                
                # Extract the variable name
                name_match = re.search(r'name\s+=\s+"(PMUSER_[^"]+)"', var_block)
                if not name_match:
                    continue
                
                full_name = name_match.group(1)
                if not full_name.startswith("PMUSER_"):
                    continue
                
                # Strip the "PMUSER_" prefix to get the key
                key = full_name[7:]  # Skip "PMUSER_"
                
                # Extract other fields
                description_match = re.search(r'description\s+=\s+"([^"]*)"', var_block)
                description = description_match.group(1) if description_match else ""
                
                value_match = re.search(r'value\s+=\s+"([^"]*)"', var_block)
                value = value_match.group(1) if value_match else ""
                
                hidden_match = re.search(r'hidden\s+=\s+(true|false)', var_block)
                hidden = hidden_match.group(1) == "true" if hidden_match else False
                
                sensitive_match = re.search(r'sensitive\s+=\s+(true|false)', var_block)
                sensitive = sensitive_match.group(1) == "true" if sensitive_match else False
                
                # Store the extracted data
                results[key] = {
                    "description": description,
                    "value": value,
                    "hidden": hidden,
                    "sensitive": sensitive
                }
                
                # Store the position information for later replacement
                var_block_positions.append((var_block_start, var_block_end))
            
            # Store the positions of all variable blocks for this data block
            if var_block_positions:
                self.variable_blocks_positions.append({
                    "data_name": data_name,
                    "data_start": data_start,
                    "data_end": data_end,
                    "var_positions": var_block_positions
                })
        
        self.extracted_pmuser_vars = results
        return results

    def update_variables_tf(self, input_dir, output_dir) -> None:
        """
        Update variables.tf with the pmuser_variables definition
        """
        # Check if the pmuser_variables variable is already defined

        input_variables_file_path = os.path.join(input_dir, self.variables_file)
        output_variables_file_path = os.path.join(output_dir, self.variables_file)

        pmuser_var_defined = False
        if os.path.exists(input_variables_file_path):
            with open(input_variables_file_path, 'r') as f:
                content = f.read()
                pmuser_var_defined = 'variable "pmuser_variables"' in content
        
        # Copy the file
        shutil.copy(input_variables_file_path, output_variables_file_path)

        # Create or append to variables.tf
        mode = 'a' if os.path.exists(output_variables_file_path) else 'w'
        with open(output_variables_file_path, mode) as f:
            if not pmuser_var_defined:
                f.write("""
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
""")
                print(f"Added pmuser_variables definition to {output_variables_file_path}")
            else:
                print(f"pmuser_variables is already defined in {output_variables_file_path}")

    def update_tfvars(self, output_dir) -> None:
        """
        Update terraform.tfvars with the extracted PMUSER variables
        """
        tfvars_file_path = os.path.join(output_dir, self.tfvars_file)

        existing_content = ""
        if os.path.exists(tfvars_file_path):
            with open(tfvars_file_path, 'r') as f:
                existing_content = f.read()
        
        # Check if the pmuser_variables are already defined
        if "pmuser_variables = {" in existing_content:
            print(f"pmuser_variables is already defined in {tfvars_file_path}. Skipping update.")
            return
        
        # Format the pmuser_variables map
        tfvars_content = "pmuser_variables = {\n"
        for key, attrs in self.extracted_pmuser_vars.items():
            tfvars_content += f'  "{key}" = {{\n'
            tfvars_content += f'    description = "{attrs["description"]}"\n'
            tfvars_content += f'    value       = "{attrs["value"]}"\n'
            tfvars_content += f'    hidden      = {str(attrs["hidden"]).lower()}\n'
            tfvars_content += f'    sensitive   = {str(attrs["sensitive"]).lower()}\n'
            tfvars_content += "  },\n"
        tfvars_content += "}\n"
        
        # Append to existing file or create a new one
        with open(tfvars_file_path, 'a') as f:
            f.write("\n" + tfvars_content)
            
        print(f"Added pmuser_variables to {tfvars_file_path} with {len(self.extracted_pmuser_vars)} entries")

    def replace_variable_blocks(self, input_dir, output_dir) -> None:
        """
        Replace individual variable blocks with a dynamic block
        """

        input_rules_file_path = os.path.join(input_dir, self.rules_file)
        output_rules_file_path = os.path.join(output_dir, self.rules_file)

        # Copy the file
        shutil.copy(input_rules_file_path, output_rules_file_path)

        if not self.variable_blocks_positions:
            print("No variable blocks to replace")
            return
        
        # Read the entire file
        with open(output_rules_file_path, 'r') as f:
            content = f.read()
            
        # Make a backup of the original file
        backup_file = f"{output_rules_file_path}.bak"
        with open(backup_file, 'w') as f:
            f.write(content)
        print(f"Created backup of {output_rules_file_path} to {backup_file}")
        
        # Process each data block
        # We need to process them in reverse order to avoid position shifts
        for data_block_info in reversed(self.variable_blocks_positions):
            data_name = data_block_info["data_name"]
            var_positions = data_block_info["var_positions"]
            
            # Sort positions in reverse order to avoid offsets when making replacements
            var_positions.sort(reverse=True)
            
            # If there are no variable blocks, continue
            if not var_positions:
                continue
                
            # Find the start of the first `variable` block (including the `variable` keyword)
            first_start = min(pos[0] for pos in var_positions)
            
            # Adjust `first_start` to include the `variable` keyword
            # Search backward from the first block's start to find the `variable` keyword
            variable_keyword_start = content.rfind("variable", 0, first_start)
            if variable_keyword_start == -1:
                print(f"Could not find 'variable' keyword for {data_name}. Skipping replacement.")
                continue
            
            # Find the end of the last `variable` block
            last_end = max(pos[1] for pos in var_positions)
            
            # Create the dynamic block
            dynamic_block = """dynamic "variable" {
      for_each = var.pmuser_variables
      content {
        name        = "PMUSER_${upper(variable.key)}"
        description = variable.value.description
        value       = variable.value.value
        hidden      = variable.value.hidden
        sensitive   = variable.value.sensitive
      }
    }"""
            
            # Replace all variable blocks with the dynamic block
            # Ensure we remove the original `variable` keyword and its blocks
            content = content[:variable_keyword_start] + dynamic_block + content[last_end:]
            
            print(f"Replaced {len(var_positions)} variable blocks in {data_name} with a dynamic block")
        
        # Write the modified content back
        with open(output_rules_file_path, 'w') as f:
            f.write(content)
            
        print(f"Updated {output_rules_file_path} with dynamic blocks for PMUSER variables")

    def move_rules_tf(self, input_dir, output_dir):
        input_rules_file_path = os.path.join(input_dir, self.rules_file)
        output_rules_file_path = os.path.join(output_dir, self.rules_file)

        # Copy the file
        shutil.copy(input_rules_file_path, output_rules_file_path)


def pmuser_to_dynamic(input_dir, output_dir: List[str] = None):
    
    converter = TerraformPropertyVariablesConverter(rules_file="rules.tf")
    extracted_vars = converter.parse_rules_file(input_dir)
    
    print("Extracted PMUSER variables:")
    for key, attrs in extracted_vars.items():
        print(f"  {key}: {attrs}")
    
    if extracted_vars:
        converter.update_variables_tf(input_dir, output_dir)
        converter.update_tfvars(output_dir)
        converter.replace_variable_blocks(input_dir, output_dir)
    else:
        converter.move_rules_tf(input_dir, output_dir)
        print("No PMUSER variables were extracted. Check if the file structure matches the expected format.")


if __name__ == "__main__":
    # Specify the variables you want to include in terraform.tfvars
    pmuser_to_dynamic(input_dir=".", output_dir="./result")