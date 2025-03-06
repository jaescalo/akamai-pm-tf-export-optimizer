import os
import re
from typing import Dict, List, Tuple

class TerraformImportConverter:
    def __init__(self, import_sh_file: str = "import.sh", import_tf_file: str = "import.tf"):
        self.import_sh_file = import_sh_file
        self.import_tf_file = import_tf_file
        
    def parse_import_commands(self, input_dir: str) -> List[Tuple[str, str, str]]:
        """
        Parse the terraform import commands from import.sh file.
        Returns a list of tuples: (resource_type, resource_name, resource_id)
        """
        import_sh_path = os.path.join(input_dir, self.import_sh_file)
        
        if not os.path.exists(import_sh_path):
            print(f"Error: File {import_sh_path} not found")
            return []
            
        with open(import_sh_path, 'r') as f:
            content = f.read()
            
        # Extract import commands using regex
        import_commands = re.findall(r'terraform import ([\w_]+)\.([\w_.-]+) (.+)', content)
        return import_commands
        
    def generate_import_tf(self, input_dir: str, output_dir: str) -> None:
        """
        Generate import.tf with import blocks using the new Terraform format.
        """
        import_commands = self.parse_import_commands(input_dir)
        
        if not import_commands:
            print("No import commands found in import.sh. Skipping import.tf generation.")
            return
            
        import_blocks = []
        
        for resource_type, resource_name, resource_id in import_commands:
            # Handle edge_hostnames specially
            if resource_type == "akamai_edge_hostname":
                to_value = f'module.akamai_property.akamai_edge_hostname.edge_hostnames["{resource_name}"]'
            else:
                to_value = f'module.akamai_property.{resource_type}.{resource_name}'
                
            import_block = 'import {\n'
            import_block += f'  to = {to_value}\n'
            import_block += f'  id = "{resource_id}"\n'
            import_block += '}\n'
            import_blocks.append(import_block)
            
        # Write the import blocks to import.tf
        output_import_tf_path = os.path.join(output_dir, self.import_tf_file)
        with open(output_import_tf_path, 'w') as f:
            f.write('\n'.join(import_blocks))
            
        print(f"Generated {output_import_tf_path} with {len(import_commands)} import blocks.")

def convert_imports(input_dir: str, output_dir: str) -> None:
    """
    Convert terraform import commands to the new import block format.
    """
    converter = TerraformImportConverter()
    converter.generate_import_tf(input_dir, output_dir)

if __name__ == "__main__":
    # For local module testing
    convert_imports(input_dir="../test", output_dir="../result")