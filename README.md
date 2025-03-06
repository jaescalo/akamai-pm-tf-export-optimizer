# Parameterize and Modularize Property Manager Terraform Export

This tool takes a Property Manager (PM) Terraform [export](https://github.com/akamai/cli-terraform) as an input and restructure it into a reusable structure that can support multiple environments (e.g. dev, qa, prod).

## Requirements
- Terraform v1.9.0 or above
- Akamai Provider v7.0.0 or above
- A PM Terraform export performed with the [Akamai Terraform CLI](https://github.com/akamai/cli-terraform?tab=readme-ov-file#property-manager-properties) using only the `--rules-as-hcl` option. As of cli-terraform v2.0.0 other options like `--akamai-property-bootstrap` and `--split-depth` are available which restructure the Terraform project. Don't use these additional options for this tool to run properly.

## Usage
```
$ python3 main.py optimize --help
Usage: main.py optimize [OPTIONS]

Options:
  -i, --input-dir PATH   Directory to read the input files.  [required]
  -d, --depth INTEGER    Maximum depth of rule hierarchy to split into
                         separate files. Default is 1.
  -o, --output-dir TEXT  Directory to write output files. Default is current
                         directory.
  --help                 Show this message and exit.
```

## Project Restructuring Details

The [Akamai Terraform CLI](https://github.com/akamai/cli-terraform?tab=readme-ov-file#property-manager-properties) output results in the following structure:
```bash
.
├── import.sh
├── property.tf
├── rules.tf
└── variables.tf
```

This Python tool will:
1. Create a new folder `./environments/prod`. The `prod` sub-directory can be duplicated for adding more environments to the project. This directory will contain the main Terraform file and is the location from where you would execute your `terraform` commands.
2. Parameterize the rule tree to allow for code reusability. Specially handy for low level environments (e.g. dev ,qa, etc). By default the following values are parameterized and variables created in the `variables.tf` and `terraform.tfvars` files:
    * All PMUSER variables
    * Origin hostnames for the origin behavior
    * CP Code IDs for the CP code behavior
3. Create the `modules/property` folder where all the property related Terraform resources and rule tree data sources will be stored. The rule tree is also broken down into multiple `*.tf` if the depth is specified as option for this tool.
4. The `import.sh` script is substituted by the `import.tf` which uses Terraform inline `import` blocks to import the resources instead. The file is located under the `environments/prod` directory.

The resulting structure will look like this:

```bash
.
├── environments
│   └── prod
│       ├── import.tf
│       ├── main.tf
│       ├── provider.tf
│       ├── terraform.tfvars
│       ├── variables.tf
│       └── versions.tf
└── modules
    └── property
        ├── caching.tf
        ├── cors_support.tf
        ├── debugging.tf
        ├── default.tf
        ├── image_and_video_manager_-_images-.tf
        ├── logging.tf
        ├── m_tls.tf
        ├── origins.tf
        ├── property.tf
        ├── variables.tf
        └── versions.tf
```

## Terraform Deployments
Go to the `environments/prod` folder to initialize and run Terraform. 
```bash
terraform init
terraform plan #Optional
terraform apply
```

Terraform will import the existing resources to its state and apply any changes you may have introduced into the code. 


### Additional Environments (Properties)
To add more properties, for example the low level environment properties (i.e. dev, qa):
1. Clone the `prod` folder and rename it to reflect the environment. For instance for the qa environment you'll and up with `environments/qa`. 
2. Modify all the parameters in the `terraform.tfvars` according to the qa environment.
3. Run the same [terraform commands](#terraform-deployments) assuming the qa property exists in Akamai. 

If the intention is to create new properties based on the initial export then you must add all the correct parameters in the `terraform.tfvars` and remove the `import.tf` from the project. When you run Terraform it will create all new resources. 

