import re
import os
from typing import Dict, List, Any


class TerraformRulesParser:
    def __init__(self, rules_file: str = "rules.tf"):
        self.rules_file = rules_file
        self.variables_file = "variables.tf"
        self.tfvars_file = "terraform.tfvars"
        self.extracted_values = {}
        self.replacements = {}  # Tracks positions for replacements

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

    def parse_rules_file(self, target_paths: List[List[str]], output_dir) -> Dict[str, str]:
        """
        Parse the rules.tf file and extract values based on specified paths
        Each path is a list of strings representing nested keys to follow
        Example: ["behavior", "origin", "hostname"]
        """
        input_rules_file_path = os.path.join(output_dir, self.rules_file)

        try:
            with open(input_rules_file_path, 'r') as f:
                content = f.read()
        except FileNotFoundError:
            print(f"Error: File {input_rules_file_path} not found")
            return {}
        
        results = {}
        
        # Find all data blocks for akamai_property_rules_builder
        data_block_pattern = r'data\s+"akamai_property_rules_builder"\s+"([^"]+)"\s+{'
        for match in re.finditer(data_block_pattern, content):
            data_name = match.group(1)
            block_start = match.end() - 1  # Position of the opening brace
            
            # Extract the complete data block
            data_block, _, _ = self._extract_block_content(content, block_start)
            if not data_block:
                continue
            
            # Extract the suffix (after "rule_")
            suffix_match = re.search(r'rule_(.+)$', data_name)
            if not suffix_match:
                continue
            
            suffix = suffix_match.group(1)
            
            # Find the rules_v* block
            rules_pattern = r'rules_v[0-9_]+\s+{'
            rules_match = re.search(rules_pattern, data_block)
            if not rules_match:
                continue
                
            rules_start = rules_match.end() - 1 + block_start
            rules_block, rules_block_start, rules_block_end = self._extract_block_content(content, rules_start)
            
            # Process each target path
            for path in target_paths:
                if len(path) < 2:
                    continue
                
                behavior_type = path[0]
                param_path = path[1:]
                
                # Match the behavior
                behavior_pattern = rf'{behavior_type}\s+{{'
                for behavior_match in re.finditer(behavior_pattern, rules_block):
                    behavior_start = behavior_match.end() - 1 + rules_block_start
                    behavior_block, behavior_block_start, behavior_block_end = self._extract_block_content(content, behavior_start)
                    
                    # Navigate through the nested structure
                    current_block = behavior_block
                    current_start = behavior_block_start
                    
                    for i, key in enumerate(param_path[:-1]):
                        key_pattern = rf'{key}\s+{{'
                        key_match = re.search(key_pattern, current_block)
                        if not key_match:
                            break
                        
                        key_start = key_match.end() - 1 + current_start
                        current_block, current_start, current_end = self._extract_block_content(content, key_start)
                    else:
                        # We've navigated to the correct nesting level, now extract the target value
                        final_key = param_path[-1]
                        
                        # Try to match string value with the exact key name
                        value_pattern = rf'(?<!\w){final_key}\s+=\s+"([^"]+)"'
                        value_match = re.search(value_pattern, current_block)
                        is_string = True
                        
                        # If not a string, try number
                        if not value_match:
                            value_pattern = rf'(?<!\w){final_key}\s+=\s+(\d+)'
                            value_match = re.search(value_pattern, current_block)
                            is_string = False
                        
                        if value_match:
                            value = value_match.group(1)
                            var_name = f"{suffix}_{behavior_type}_{final_key}"
                            results[var_name] = value
                            
                            # Calculate the exact position in the file for replacement
                            pattern_start = value_match.start(0) + current_start
                            value_start = value_match.start(1) + current_start
                            value_end = value_match.end(1) + current_start
                            key_text = content[pattern_start:value_start-1]  # The text before the value (includes the key name)
                            
                            # Store replacement information
                            self.replacements[var_name] = {
                                'pattern_start': pattern_start,
                                'value_start': value_start,
                                'value_end': value_end,
                                'key_text': key_text,
                                'original': value,
                                'is_string': is_string
                            }
                            
                            print(f"Found {var_name} = {value}")
        
        self.extracted_values = results
        return results

    def update_variables_tf(self, output_dir) -> None:
        """
        Update variables.tf with variable definitions
        """
        variables_file_path = os.path.join(output_dir, self.variables_file)

        # Create or append to variables.tf
        mode = 'a' if os.path.exists(variables_file_path) else 'w'
        with open(variables_file_path, mode) as f:
            # Prepare new variable definitions
            new_vars_content = ""
            for var_name, value in self.extracted_values.items():
                # Determine type based on value
                var_type = "string"
                if value.isdigit():
                    var_type = "number"
                
                new_vars_content += f'''
variable "{var_name}" {{
  description = "Extracted from Terraform rules file"
  type        = {var_type}
}}
'''
            f.write(new_vars_content)
                   
        print(f"Updated {variables_file_path} with {len(self.extracted_values)}")

    def update_tfvars(self, output_dir) -> None:
        """
        Update terraform.tfvars with extracted values
        """
        tfvars_file_path = os.path.join(output_dir, self.tfvars_file)

        # Create or append to variables.tf
        mode = 'a' if os.path.exists(tfvars_file_path) else 'w'
        with open(tfvars_file_path, mode) as f:
            # Then write all new values
            for var_name, value in self.extracted_values.items():
                if value.isdigit():
                    f.write(f"{var_name} = {value}\n")
                else:
                    f.write(f'{var_name} = "{value}"\n')

        print(f"Updated {tfvars_file_path} with {len(self.extracted_values)} values")

    def replace_hardcoded_values(self, output_dir) -> None:
        """
        Replace hardcoded values in rules.tf with variable references
        """
        input_rules_file_path = os.path.join(output_dir, self.rules_file)

        if not self.replacements:
            print("No replacements to make")
            return
            
        # Read the entire file
        with open(input_rules_file_path, 'r') as f:
            content = f.read()
            
        # Make a backup of the original file
        backup_file = f"{input_rules_file_path}.bak"
        with open(backup_file, 'w') as f:
            f.write(content)
        print(f"Created backup of {input_rules_file_path} to {backup_file}")
        
        # Sort replacements by position (descending) to avoid offset issues
        sorted_replacements = sorted(
            self.replacements.items(), 
            key=lambda x: x[1]['pattern_start'], 
            reverse=True
        )
        
        # Make the replacements
        for var_name, rep_info in sorted_replacements:
            pattern_start = rep_info['pattern_start']
            value_start = rep_info['value_start']
            value_end = rep_info['value_end']
            key_text = rep_info['key_text']
            is_string = rep_info['is_string']
            
            # Create the variable reference
            var_ref = f"var.{var_name}"
            
            if is_string:
                # For string values, we need to handle the quotes
                # Check if there's a closing quote after the value
                if content[value_end:value_end+1] == '"':
                    # If there is, extend value_end to include it
                    value_end += 1
                    
            # Replace in content (from pattern_start to value_end)
            replacement = f"{key_text}{var_ref}"
            content = content[:pattern_start] + replacement + content[value_end:]
            
        # Write the modified content back
        with open(input_rules_file_path, 'w') as f:
            f.write(content)
            
        print(f"Replaced {len(self.replacements)} hardcoded values with variable references in {input_rules_file_path}")


def rule_tree_parameterization(output_dir):
    # Define paths to extract
    # Format: [behavior_type, nested_key1, nested_key2, ..., target_parameter]
    target_paths = [
        ["origin", "hostname"],
        ["cp_code", "value", "id"]
    ]

    parser = TerraformRulesParser(rules_file="rules.tf")
    extracted = parser.parse_rules_file(target_paths, output_dir)
    
    print("Extracted values:")
    for var_name, value in extracted.items():
        print(f"{var_name} = {value}")
    
    if extracted:
        parser.update_variables_tf(output_dir)
        parser.update_tfvars(output_dir)
        parser.replace_hardcoded_values(output_dir)
    else:
        print("No values were extracted. Check if the file structure matches the expected format.")

if __name__ == "__main__":
    rule_tree_parameterization(output_dir="../result")