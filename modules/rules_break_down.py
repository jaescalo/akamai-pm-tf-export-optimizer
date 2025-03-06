import re
import os

def extract_rule_block(content, rule_name):
    # Find the start position of the rule
    rule_start_pattern = re.compile(rf'data "akamai_property_rules_builder" "{rule_name}"')
    start_match = rule_start_pattern.search(content)
    
    if not start_match:
        return None
    
    start_pos = start_match.start()
    
    # Now find the end of the block by counting braces
    brace_count = 0
    inside_string = False
    inside_comment = False
    pos = start_pos
    
    while pos < len(content):
        char = content[pos]
        
        # Skip over string literals
        if char == '"' and (pos == 0 or content[pos-1] != '\\'):
            inside_string = not inside_string
        
        # Skip over comments
        if not inside_string and char == '#':
            inside_comment = True
        if inside_comment and char == '\n':
            inside_comment = False
        
        if not inside_string and not inside_comment:
            if char == '{':
                brace_count += 1
            elif char == '}':
                brace_count -= 1
                if brace_count == 0:
                    # We've found the end of the block
                    end_pos = pos + 1
                    return content[start_pos:end_pos]
        
        pos += 1
    
    return None

def extract_children_names(rule_block):
    # Extract child rule references from the children attribute
    children_pattern = r'children\s*=\s*\[\s*(.*?)\s*\]'
    children_match = re.search(children_pattern, rule_block, re.DOTALL)
    
    if not children_match:
        return []
    
    # Extract the rule names from the references
    children_str = children_match.group(1)
    child_refs = re.findall(r'data\.akamai_property_rules_builder\.([\w-]+)\.json', children_str)
    return child_refs

def collect_rule_hierarchy(content, rule_names_dict, rule_name, parent_path=None):
    """
    Build a dictionary that maps each rule to its hierarchy path and collect child rules.
    
    Args:
        content: The content of the terraform file
        rule_names_dict: Dictionary to store rule hierarchy information
        rule_name: Current rule name to process
        parent_path: Path to the current rule from the root
    
    Returns:
        Dictionary mapping rule names to their children
    """
    if parent_path is None:
        parent_path = []
    
    current_path = parent_path + [rule_name]
    rule_names_dict[rule_name] = {
        'path': current_path,
        'level': len(current_path) - 1,  # Default rule is level 0
        'children': []
    }
    
    # Get the rule block
    rule_block = extract_rule_block(content, rule_name)
    if rule_block:
        # Find children of this rule
        children = extract_children_names(rule_block)
        rule_names_dict[rule_name]['children'] = children
        
        # Process each child recursively
        for child_name in children:
            collect_rule_hierarchy(content, rule_names_dict, child_name, current_path)
    
    return rule_names_dict

def get_rule_file_mapping(rule_hierarchy, max_depth):
    """
    Determine which file each rule should be written to based on the max_depth.
    
    Args:
        rule_hierarchy: Dictionary containing rule hierarchy information
        max_depth: Maximum depth of rules to split into separate files
    
    Returns:
        Dictionary mapping rule names to their target output file names
    """
    file_mapping = {}
    
    for rule_name, info in rule_hierarchy.items():
        level = info['level']
        
        if level <= max_depth:
            # This rule gets its own file
            base_name = rule_name.split('_rule_')[-1] if '_rule_' in rule_name else rule_name
            file_mapping[rule_name] = base_name
        else:
            # Find the ancestor at max_depth to determine which file this rule belongs to
            ancestor_rule_name = info['path'][max_depth]
            ancestor_base_name = ancestor_rule_name.split('_rule_')[-1] if '_rule_' in ancestor_rule_name else ancestor_rule_name
            file_mapping[rule_name] = ancestor_base_name
    
    return file_mapping

def split_terraform_file(output_dir, depth):
    """Split a Terraform file containing Akamai property rules into multiple files based on rule hierarchy."""
    
    rules_file_path = os.path.join(output_dir, "rules.tf")
    module_output_dir = os.path.join(output_dir, "modules/property")

    with open(rules_file_path, 'r') as f:
        content = f.read()
    
    # Ensure output directory exists
    if not os.path.exists(module_output_dir):
        os.makedirs(module_output_dir)
    
    # Find all rule declarations
    rule_declarations = re.findall(r'data "akamai_property_rules_builder" "([\w-]+)"', content)
    
    # Find the default rule
    default_rule_name = next((name for name in rule_declarations if '_rule_default' in name), None)
    if not default_rule_name:
        print("Default rule not found!")
        return
    
    # Build the rule hierarchy
    rule_hierarchy = collect_rule_hierarchy(content, {}, default_rule_name)
    
    # Determine which file each rule should go to
    file_mapping = get_rule_file_mapping(rule_hierarchy, depth)
    
    # Group rules by target file
    file_contents = {}
    for rule_name, target_file in file_mapping.items():
        if target_file not in file_contents:
            file_contents[target_file] = []
        
        rule_block = extract_rule_block(content, rule_name)
        if rule_block:
            file_contents[target_file].append(rule_block)
        else:
            print(f"Failed to extract {rule_name} block!")
    
    # Write the files
    for base_name, blocks in file_contents.items():
        output_file = os.path.join(module_output_dir, f"{base_name}.tf")
        with open(output_file, 'w') as f:
            f.write("\n\n".join(blocks))
        print(f"Created {output_file} with {len(blocks)} rule(s)")
    
    print(f"Successfully split {rules_file_path} into {len(file_contents)} files with max depth {depth}")

if __name__ == "__main__":
    split_terraform_file(output_dir="../result", depth="1")