import click
from modules import rules_break_down
from modules import convert_pmuser
from modules import rules_parameterization
from modules import property_parameterization
from modules import vars_to_tfvars
from modules import generate_main_tf
from modules import restructure_project
from modules import convert_imports_tf

@click.group()
def cli():
    """Main CLI entry point for the application"""
    pass

@cli.command()
@click.option('--input-dir', '-i', type=click.Path(exists=True), help="Directory to read the input files.", required=True)
@click.option('--depth', '-d', default=1, help='Maximum depth of rule hierarchy to split into separate files. Default is 1.')
@click.option('--output-dir', '-o', default='.', help='Directory to write output files. Default is current directory.')
def optimize(input_dir, depth, output_dir):
    vars_to_tfvars.filter_vars(input_dir, output_dir)
    convert_pmuser.pmuser_to_dynamic(input_dir, output_dir)
    rules_parameterization.rule_tree_parameterization(output_dir)
    rules_break_down.split_terraform_file(output_dir, depth)
    property_parameterization.parameterize_property_resources(input_dir, output_dir)
    generate_main_tf.main_tf(output_dir)
    convert_imports_tf.convert_imports(input_dir, output_dir)
    restructure_project.restructure_and_cleanup(output_dir)
    
    click.echo(f"Processing complete")

if __name__ == '__main__':
    cli()