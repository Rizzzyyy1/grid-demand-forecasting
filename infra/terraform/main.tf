# One small host runs the same docker-compose stack as a laptop; S3 keeps nightly backups of
# data/ and reports/. Deliberately not Kubernetes/ECS: one daily batch job and two read-only
# web apps do not need an orchestrator (docs/adr/0008-single-host-deployment.md).

data "aws_ssm_parameter" "ubuntu_arm64" {
  name = "/aws/service/canonical/ubuntu/server/24.04/stable/current/arm64/hvm/ebs-gp3/ami-id"
}

resource "aws_s3_bucket" "backups" {
  bucket_prefix = "gridcast-backups-"
  force_destroy = true
}

resource "aws_s3_bucket_versioning" "backups" {
  bucket = aws_s3_bucket.backups.id
  versioning_configuration { status = "Enabled" }
}

resource "aws_s3_bucket_public_access_block" "backups" {
  bucket                  = aws_s3_bucket.backups.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_server_side_encryption_configuration" "backups" {
  bucket = aws_s3_bucket.backups.id
  rule {
    apply_server_side_encryption_by_default { sse_algorithm = "AES256" }
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "backups" {
  bucket = aws_s3_bucket.backups.id
  rule {
    id     = "expire-old-versions"
    status = "Enabled"
    filter {}
    noncurrent_version_expiration { noncurrent_days = 30 }
  }
}

data "aws_iam_policy_document" "assume_ec2" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["ec2.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "host" {
  name_prefix        = "gridcast-host-"
  assume_role_policy = data.aws_iam_policy_document.assume_ec2.json
}

data "aws_iam_policy_document" "backups" {
  statement {
    actions   = ["s3:PutObject", "s3:GetObject", "s3:ListBucket"]
    resources = [aws_s3_bucket.backups.arn, "${aws_s3_bucket.backups.arn}/*"]
  }
}

resource "aws_iam_role_policy" "backups" {
  role   = aws_iam_role.host.id
  policy = data.aws_iam_policy_document.backups.json
}

resource "aws_iam_role_policy_attachment" "ssm" {
  role       = aws_iam_role.host.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

resource "aws_iam_instance_profile" "host" {
  name_prefix = "gridcast-host-"
  role        = aws_iam_role.host.name
}

resource "aws_security_group" "host" {
  name_prefix = "gridcast-"
  description = "Public dashboard/API on 80; admin UIs and SSH only from admin_cidr"

  ingress {
    description = "Caddy: dashboard and API"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
  dynamic "ingress" {
    for_each = { ssh = 22, dagster = 3000, mlflow = 5001 }
    content {
      description = ingress.key
      from_port   = ingress.value
      to_port     = ingress.value
      protocol    = "tcp"
      cidr_blocks = [var.admin_cidr]
    }
  }
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_instance" "host" {
  ami                    = data.aws_ssm_parameter.ubuntu_arm64.value
  instance_type          = var.instance_type
  iam_instance_profile   = aws_iam_instance_profile.host.name
  vpc_security_group_ids = [aws_security_group.host.id]
  user_data = templatefile("${path.module}/cloud-init.yaml.tftpl", {
    repo_url = var.repo_url
    git_ref  = var.git_ref
    bucket   = aws_s3_bucket.backups.bucket
  })
  user_data_replace_on_change = true

  root_block_device {
    volume_size = var.root_volume_gb
    volume_type = "gp3"
    encrypted   = true
  }
  metadata_options {
    http_tokens = "required" # IMDSv2 only
  }
}

resource "aws_eip" "host" {
  instance = aws_instance.host.id
  domain   = "vpc"
}

resource "aws_budgets_budget" "monthly" {
  name         = "gridcast-monthly"
  budget_type  = "COST"
  limit_amount = tostring(var.monthly_budget_usd)
  limit_unit   = "USD"
  time_unit    = "MONTHLY"
  cost_filter {
    name   = "TagKeyValue"
    values = ["user:project$gridcast"]
  }
  notification {
    comparison_operator        = "GREATER_THAN"
    threshold                  = 80
    threshold_type             = "PERCENTAGE"
    notification_type          = "FORECASTED"
    subscriber_email_addresses = [var.budget_email]
  }
}
