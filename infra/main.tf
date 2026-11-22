terraform {
  required_version = ">= 1.6"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project   = "meetup-rsvp"
      ManagedBy = "terraform"
    }
  }
}

# ---------- Network: our own small VPC with one public subnet ----------

data "aws_availability_zones" "available" {
  state = "available"
}

resource "aws_vpc" "main" {
  cidr_block           = "10.0.0.0/16"
  enable_dns_support   = true
  enable_dns_hostnames = true
  tags                 = { Name = "meetup-rsvp-vpc" }
}

resource "aws_internet_gateway" "main" {
  vpc_id = aws_vpc.main.id
  tags   = { Name = "meetup-rsvp-igw" }
}

resource "aws_subnet" "public" {
  vpc_id            = aws_vpc.main.id
  cidr_block        = "10.0.1.0/24"
  availability_zone = data.aws_availability_zones.available.names[0]
  tags              = { Name = "meetup-rsvp-public" }
}

resource "aws_route_table" "public" {
  vpc_id = aws_vpc.main.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.main.id
  }

  tags = { Name = "meetup-rsvp-public-rt" }
}

resource "aws_route_table_association" "public" {
  subnet_id      = aws_subnet.public.id
  route_table_id = aws_route_table.public.id
}

# ---------- Firewall: web traffic from anyone, SSH only from your IP ----------

resource "aws_security_group" "web" {
  name        = "meetup-rsvp-web"
  description = "HTTP/HTTPS from anywhere, SSH from my IP only"
  vpc_id      = aws_vpc.main.id

  ingress {
    description = "HTTP (Caddy redirects to HTTPS and uses it for the certificate check)"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description = "HTTPS"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description = "SSH from my IP only"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["${var.my_ip}/32"]
  }

  egress {
    description = "Outbound (apt, Docker Hub, GitHub, Google sign-in)"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

# ---------- A fixed public IP, so the app's address never changes ----------

resource "aws_eip" "app" {
  domain = "vpc"
  tags   = { Name = "meetup-rsvp-ip" }
}

locals {
  # e.g. 3.25.10.7 -> 3-25-10-7.sslip.io (a free DNS name that points at that IP)
  domain = "${replace(aws_eip.app.public_ip, ".", "-")}.sslip.io"
}

# ---------- The server ----------

# Ask AWS for the latest official Ubuntu 24.04 (ARM) image, published by Canonical
data "aws_ssm_parameter" "ubuntu" {
  name = "/aws/service/canonical/ubuntu/server/24.04/stable/current/arm64/hvm/ebs-gp3/ami-id"
}

resource "aws_key_pair" "me" {
  key_name   = "meetup-rsvp-key"
  public_key = file(pathexpand(var.ssh_public_key_path))
}

resource "aws_instance" "app" {
   ami                    = data.aws_ssm_parameter.ubuntu.value
  instance_type          = var.instance_type
  subnet_id              = aws_subnet.public.id
  vpc_security_group_ids = [aws_security_group.web.id]
  key_name               = aws_key_pair.me.key_name

  root_block_device {
    volume_type = "gp3"
    volume_size = 20
    encrypted   = true
  }

  metadata_options {
    http_tokens = "required" # IMDSv2 only
  }

  user_data_base64 = base64encode(templatefile("${path.module}/user_data.sh.tpl", {
    repo_url             = var.repo_url
    domain               = local.domain
    google_client_id     = var.google_client_id
    google_client_secret = var.google_client_secret
    session_secret       = var.session_secret
  }))

  # Changing the startup script means building a fresh server.
  user_data_replace_on_change = true

  tags = { Name = "meetup-rsvp-server" }
}

resource "aws_eip_association" "app" {
  instance_id   = aws_instance.app.id
  allocation_id = aws_eip.app.id
}