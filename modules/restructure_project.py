import os
import re
import shutil


class TerraformProjectRestructure:
    def __init__(self, output_dir: str = "./result"):
        self.input_dir = output_dir
        self.output_dir = output_dir
        self.modules_dir = os.path.join(output_dir, "modules", "property")
        self.environments_dir = os.path.join(output_dir, "environments", "prod")

    def split_property_tf(self) -> None:
        """
        Split property.tf into versions.tf, provider.tf, and property.tf.
        """
        property_tf_path = os.path.join(self.input_dir, "property.tf")

        if not os.path.exists(property_tf_path):
            print(f"Error: File {property_tf_path} not found")
            return

        with open(property_tf_path, 'r') as f:
            content = f.read()

        # Extract the terraform block
        terraform_block = self._extract_terraform_block(content)
        if terraform_block:
            versions_tf_path = os.path.join(self.input_dir, "versions.tf")
            with open(versions_tf_path, 'w') as f:
                f.write(terraform_block)
            print(f"Created {versions_tf_path} with terraform block")

        # Extract the provider block
        provider_block = self._extract_provider_block(content)
        if provider_block:
            provider_tf_path = os.path.join(self.input_dir, "provider.tf")
            with open(provider_tf_path, 'w') as f:
                f.write(provider_block)
            print(f"Created {provider_tf_path} with provider block")

        # Remove terraform and provider blocks from property.tf
        remaining_content = self._remove_terraform_and_provider_blocks(content)

        # Write the remaining content to property.tf
        with open(property_tf_path, 'w') as f:
            f.write(remaining_content.strip())
        print(f"Updated {property_tf_path} by removing terraform and provider blocks")

    def _extract_terraform_block(self, content: str) -> str:
        """
        Extract the terraform block from the content, preserving nested braces and indentation.
        """
        # Start at the position of "terraform"
        terraform_pos = content.find("terraform")
        
        if terraform_pos == -1:
            return ""
        
        # Find the opening brace after "terraform"
        open_brace_pos = content.find("{", terraform_pos)
        if open_brace_pos == -1:
            return ""
        
        # Keep track of brace balance to handle nested braces
        brace_count = 1
        pos = open_brace_pos + 1
        
        # Continue until we find the matching closing brace
        while brace_count > 0 and pos < len(content):
            if content[pos] == "{":
                brace_count += 1
            elif content[pos] == "}":
                brace_count -= 1
            pos += 1
        
        # If we didn't find a matching closing brace
        if brace_count != 0:
            return ""
        
        # Extract the full terraform block
        terraform_block = content[terraform_pos:pos]
        
        # Extract just the inner content (without the outer braces)
        inner_content = content[open_brace_pos+1:pos-1].strip()
        
        # Format the block with proper indentation
        formatted_block = f'terraform {{\n{self._indent(inner_content)}\n}}\n'
        
        return formatted_block

    def _extract_provider_block(self, content: str) -> str:
        """
        Extract the provider block from the content and apply consistent indentation.
        """
        provider_pattern = r'provider\s+"[^"]+"\s+{([^}]+)}'
        match = re.search(provider_pattern, content, re.DOTALL)
        
        if match:
            # Extract the inner content
            inner_content = match.group(1).strip()
            
            # Split lines and apply consistent indentation (2 spaces)
            lines = inner_content.split('\n')
            indented_lines = []
            for line in lines:
                stripped_line = line.strip()
                if stripped_line:
                    indented_lines.append("  " + stripped_line)
            
            # Join back with newlines
            formatted_content = '\n'.join(indented_lines)
            
            return f'provider "akamai" {{\n{formatted_content}\n}}\n'
        
        return ""

    def _remove_terraform_and_provider_blocks(self, content: str) -> str:
        """
        Remove terraform and provider blocks from the content.
        """
        # Extract the blocks first
        terraform_block = self._extract_terraform_block(content)
        provider_block = self._extract_provider_block(content)
        
        # Create a clean version of the content
        remaining_content = content
        
        # Find the actual blocks in the original content
        if terraform_block:
            # Find the start of the terraform block
            terraform_start = content.find("terraform")
            if terraform_start != -1:
                # Find the end of the terraform block
                open_brace_pos = content.find("{", terraform_start)
                if open_brace_pos != -1:
                    brace_count = 1
                    pos = open_brace_pos + 1
                    
                    while brace_count > 0 and pos < len(content):
                        if content[pos] == "{":
                            brace_count += 1
                        elif content[pos] == "}":
                            brace_count -= 1
                        pos += 1
                    
                    if brace_count == 0:
                        # Remove the block including any trailing whitespace
                        end_pos = pos
                        while end_pos < len(content) and content[end_pos].isspace():
                            end_pos += 1
                        
                        remaining_content = content[:terraform_start] + content[end_pos:]
        
        # Find and remove the provider block from the remaining content
        if provider_block:
            provider_start = remaining_content.find('provider "akamai"')
            if provider_start != -1:
                open_brace_pos = remaining_content.find("{", provider_start)
                if open_brace_pos != -1:
                    brace_count = 1
                    pos = open_brace_pos + 1
                    
                    while brace_count > 0 and pos < len(remaining_content):
                        if remaining_content[pos] == "{":
                            brace_count += 1
                        elif remaining_content[pos] == "}":
                            brace_count -= 1
                        pos += 1
                    
                    if brace_count == 0:
                        # Remove the block including any trailing whitespace
                        end_pos = pos
                        while end_pos < len(remaining_content) and remaining_content[end_pos].isspace():
                            end_pos += 1
                        
                        remaining_content = remaining_content[:provider_start] + remaining_content[end_pos:]
        
        # Remove any leading/trailing whitespace and normalize newlines
        remaining_content = remaining_content.strip()
        
        return remaining_content

    def _indent(self, text: str, indent_level: int = 2) -> str:
        """
        Indent the given text by the specified number of spaces.
        """
        indent = " " * indent_level
        return indent + text.replace("\n", f"\n{indent}")

    def create_environments_prod_folder(self) -> None:
        """
        Create the ./environments/prod folder and move/copy files into it.
        """
        os.makedirs(self.environments_dir, exist_ok=True)

        # Move provider.tf, main.tf, import.tf and terraform.tfvars
        files_to_move = ["provider.tf", "main.tf", "import.tf", "terraform.tfvars"]
        for file_name in files_to_move:
            src_path = os.path.join(self.input_dir, file_name)
            if os.path.exists(src_path):
                shutil.move(src_path, os.path.join(self.environments_dir, file_name))
                print(f"Moved {file_name} to {self.environments_dir}")

        # Copy variables.tf and versions.tf
        files_to_copy = ["variables.tf", "versions.tf"]
        for file_name in files_to_copy:
            src_path = os.path.join(self.input_dir, file_name)
            if os.path.exists(src_path):
                shutil.copy(src_path, os.path.join(self.environments_dir, file_name))
                print(f"Copied {file_name} to {self.environments_dir}")

    def move_files_to_modules_property(self) -> None:
        """
        Move property.tf, versions.tf, and variables.tf to ./modules/property.
        """
        files_to_move = ["property.tf", "versions.tf", "variables.tf"]
        for file_name in files_to_move:
            src_path = os.path.join(self.input_dir, file_name)
            if os.path.exists(src_path):
                shutil.move(src_path, os.path.join(self.modules_dir, file_name))
                print(f"Moved {file_name} to {self.modules_dir}")

    def cleanup_files(self) -> None:
        """
        Remove *.bak files and rules.tf.
        """
        files_to_remove = ["rules.tf"]
        for file_name in files_to_remove:
            file_path = os.path.join(self.input_dir, file_name)
            if os.path.exists(file_path):
                os.remove(file_path)
                print(f"Removed {file_path}")

        # Remove all *.bak files
        for root, _, files in os.walk(self.input_dir):
            for file_name in files:
                if file_name.endswith(".bak"):
                    file_path = os.path.join(root, file_name)
                    os.remove(file_path)
                    print(f"Removed {file_path}")

    def restructure(self) -> None:
        """
        Restructure the Terraform project as per the requirements.
        """
        # Step 1: Split property.tf
        self.split_property_tf()

        # Step 2: Create environments/prod folder and move/copy files
        self.create_environments_prod_folder()

        # Step 3: Move files to modules/property
        self.move_files_to_modules_property()

        # Step 4: Clean up unnecessary files
        self.cleanup_files()

def restructure_and_cleanup(output_dir):
    # Create an instance of the TerraformProjectRestructure class
    restructure = TerraformProjectRestructure(output_dir)

    # Restructure the project
    restructure.restructure()

if __name__ == "__main__":
    restructure_and_cleanup(output_dir="../result")
