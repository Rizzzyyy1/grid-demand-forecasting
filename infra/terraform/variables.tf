variable "region" {
  description = "AWS region (EIA/grid data is US-centric; latency is irrelevant for a daily job)."
  type        = string
  default     = "us-east-1"
}

variable "instance_type" {
  description = "Graviton instance: the Docker image is multi-arch and the stack needs ~2 GB RAM."
  type        = string
  default     = "t4g.medium"
}

variable "repo_url" {
  description = "Git URL of this repository (public, or use a deploy key)."
  type        = string
}

variable "git_ref" {
  description = "Tag or branch to deploy."
  type        = string
  default     = "main"
}

variable "admin_cidr" {
  description = "CIDR allowed to reach SSH and the Dagster/MLflow admin UIs (e.g. your IP/32)."
  type        = string
}

variable "budget_email" {
  description = "Address that receives the monthly budget alert."
  type        = string
}

variable "monthly_budget_usd" {
  description = "Budget alert threshold."
  type        = number
  default     = 25
}

variable "root_volume_gb" {
  description = "Raw EIA files (~0.7 GB) + warehouse + images fit comfortably in 30 GB."
  type        = number
  default     = 30
}
