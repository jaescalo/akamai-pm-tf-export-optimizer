import re
import os
from typing import List


class TerraformTfvarsFilter:
    def __init__(self, variables_file: str = "variables.tf", tfvars_file: str = "terraform.tfvars"):
        self.variables_file = variables_file
        self.tfvars_file = tfvars_file

    def filter_and_generate_tfvars(self, input_dir: str, output_dir: str, filter_vars: List[str]) -> None:
        """
        Generate terraform.tfvars based on the specified variables in filter_vars
        """
        input_variables_file_path = os.path.join(input_dir, self.variables_file)
        output_tfvars_file_path = os.path.join(output_dir, self.tfvars_file)

        if not os.path.exists(input_variables_file_path):
            print(f"Error: File {input_variables_file_path} not found")
            return

        # Read the existing terraform.tfvars file (if it exists)
        existing_tfvars_content = ""
        if os.path.exists(output_tfvars_file_path):
            with open(output_tfvars_file_path, 'r') as f:
                existing_tfvars_content = f.read()

        # Extract variable blocks from variables.tf
        with open(input_variables_file_path, 'r') as f:
            content = f.read()

        variable_blocks = re.findall(r'variable\s+"([^"]+)"\s+{([^}]+)}', content, re.DOTALL)

        # Generate the new content for the filtered variables
        new_tfvars_content = ""
        for var_name, var_block in variable_blocks:
            if var_name in filter_vars:
                # Extract default value if exists
                default_match = re.search(r'default\s+=\s+(.*)', var_block)
                if default_match:
                    default_value = default_match.group(1).strip()
                    new_tfvars_content += f'{var_name} = {default_value}\n'

        # Combine the existing content with the new filtered variables
        # Ensure we don't duplicate the filtered variables if they already exist
        if new_tfvars_content:
            if existing_tfvars_content:
                # Remove any existing entries for the filtered variables to avoid duplicates
                for var_name in filter_vars:
                    existing_tfvars_content = re.sub(rf'{var_name}\s*=.*\n', '', existing_tfvars_content)
            
            # Append the new filtered variables to the existing content
            final_tfvars_content = existing_tfvars_content.strip() + "\n" + new_tfvars_content.strip() + "\n\n"
        else:
            final_tfvars_content = existing_tfvars_content + "\n\n"

        # Write the final content to terraform.tfvars
        with open(output_tfvars_file_path, 'w') as f:
            f.write(final_tfvars_content)

        print(f"Updated {output_tfvars_file_path} with filtered variables: {filter_vars}")

def filter_vars(input_dir, output_dir):
    # Specify the variables you want to include in terraform.tfvars
    filter_vars = ["activate_latest_on_staging", "activate_latest_on_production"]

    # Create an instance of the TerraformTfvarsFilter class
    tfvars_filter = TerraformTfvarsFilter()

    # Generate the filtered terraform.tfvars file
    tfvars_filter.filter_and_generate_tfvars(input_dir, output_dir, filter_vars)

if __name__ == "__main__":
    filter_vars(input_dir=".", output_dir="./result")