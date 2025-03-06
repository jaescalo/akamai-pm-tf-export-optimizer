import os
import re
from typing import List


class TerraformMainGenerator:
    def __init__(self, tfvars_file: str = "terraform.tfvars", main_tf_file: str = "main.tf"):
        self.tfvars_file = tfvars_file
        self.main_tf_file = main_tf_file

    def extract_variable_names(self, input_dir: str) -> List[str]:
        """
        Extract all variable names from the terraform.tfvars file.
        """
        tfvars_file_path = os.path.join(input_dir, self.tfvars_file)

        if not os.path.exists(tfvars_file_path):
            print(f"Error: File {tfvars_file_path} not found")
            return []

        with open(tfvars_file_path, 'r') as f:
            content = f.read()

        # Extract variable names using regex
        variable_names = re.findall(r'^([a-zA-Z_|-][a-zA-Z0-9_|-]*)\s*=', content, re.MULTILINE)
        return variable_names

    def generate_main_tf(self, input_dir: str, output_dir: str) -> None:
        """
        Generate main.tf with a call to the akamai_property module,
        passing all variables from terraform.tfvars as arguments.
        """
        # Extract variable names from terraform.tfvars
        variable_names = self.extract_variable_names(input_dir)

        if not variable_names:
            print("No variables found in terraform.tfvars. Skipping main.tf generation.")
            return

        # Generate the module block
        module_block = 'module "akamai_property" {\n'
        module_block += '  source = "../../modules/property"\n'
        for var_name in variable_names:
            module_block += f'  {var_name.ljust(30)} = var.{var_name}\n'
        module_block += '}\n'

        # Write the module block to main.tf
        output_main_tf_path = os.path.join(output_dir, self.main_tf_file)
        with open(output_main_tf_path, 'w') as f:
            f.write(module_block)

        print(f"Generated {output_main_tf_path} with {len(variable_names)} variables.")


def main_tf(output_dir):
    # Create an instance of the TerraformMainGenerator class
    main_generator = TerraformMainGenerator()
    input_dir = output_dir

    # Generate the main.tf file
    main_generator.generate_main_tf(input_dir, output_dir)

if __name__ == "__main__":
    # For local module testing
    main_tf(output_dir="../../result/")