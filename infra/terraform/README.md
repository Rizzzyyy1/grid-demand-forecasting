# GridCast on AWS (OpenTofu / Terraform)

> **Validated, intentionally not deployed.** This configuration passes `tofu validate` in CI but
> is not applied, because it would create billable resources. The live system runs at zero cost
> on GitHub Actions + GitHub Pages instead (ADR-0009).

One Graviton host runs the same `docker compose` stack as a laptop, behind Caddy on port 80;
Dagster and MLflow are reachable only from `admin_cidr`; nightly backups go to a versioned,
encrypted, private S3 bucket; a budget alert emails at 80 % of the monthly limit.

```bash
cd infra/terraform
tofu init            # or: terraform init
tofu plan  -var repo_url=https://github.com/Rizzzyyy1/grid-demand-forecasting.git -var admin_cidr=<your-ip>/32 -var budget_email=<you@example.com>
tofu apply ...       # needs AWS credentials in your shell; not run by the author's agent
tofu destroy ...     # tears everything down; the bucket is force-destroyable by design
```

Cost is dominated by the instance; check the current on-demand price of `instance_type` in your
region with the AWS pricing calculator before applying. `tofu validate` is run in CI-equivalent
checks without credentials.
