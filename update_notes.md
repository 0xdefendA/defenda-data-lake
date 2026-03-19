## terraform ##
```bash
terraform state replace-provider \
  "registry.terraform.io/-/aws" \
  "registry.terraform.io/hashicorp/aws"

terraform init -upgrade

```