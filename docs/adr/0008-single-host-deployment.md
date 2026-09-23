# ADR-0008: Deploy to one small host with Docker Compose, defined in OpenTofu/Terraform

Status: Accepted (not yet applied — needs the owner's AWS account) · 2026-09-23

## Context
The workload is one daily batch job (minutes of CPU), a weekly retrain, and two read-only web
apps. Data is under 1 GB. The forecast store is the only irreplaceable state.

## Decision
`infra/terraform/`: one Graviton EC2 instance running the repository's `docker compose` stack
behind Caddy; Dagster and MLflow restricted to an admin CIDR; SSM for shell access (IMDSv2 only,
encrypted gp3 root); nightly `aws s3 sync` of `data/` (minus re-downloadable raw files) and
`reports/` to a versioned, private, encrypted bucket; an AWS Budget alert at 80 %.
Validated with `tofu validate` without credentials.

## Rejected
* **ECS/Fargate, Kubernetes** — orchestration for one container set that runs once a day.
* **Serverless (Lambda + S3 + Athena)** — possible, but DuckDB files and the Dagster daemon want a
  long-lived process, and parity with the laptop stack is worth more here.

## Revisit when
Several independent jobs, more than one maintainer, or an SLO that one host cannot meet.
