# VPC Configuration for Crucible Platform
# Standard setup with public/private subnets across 2 AZs

# VPC with /16 CIDR block (65,536 IPs)
resource "aws_vpc" "main" {
  cidr_block           = "10.0.0.0/16"
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = merge(local.common_tags, {
    Name = "${var.project_name}-vpc"
  })
}

# Internet Gateway for public subnet access
resource "aws_internet_gateway" "main" {
  vpc_id = aws_vpc.main.id

  tags = merge(local.common_tags, {
    Name = "${var.project_name}-igw"
  })
}

# COST SAVINGS: NAT Gateways cost ~$45/month each
# Uncomment below for production HA setup
# resource "aws_eip" "nat" {
#   count  = 2
#   domain = "vpc"
# 
#   tags = merge(local.common_tags, {
#     Name = "${var.project_name}-nat-eip-${count.index + 1}"
#   })
# 
#   depends_on = [aws_internet_gateway.main]
# }

# Get available AZs
data "aws_availability_zones" "available" {
  state = "available"
}

# Public Subnets (2 AZs, /20 each = 4,096 IPs per subnet)
resource "aws_subnet" "public" {
  count                   = 2
  vpc_id                  = aws_vpc.main.id
  cidr_block              = "10.0.${count.index * 16}.0/20"
  availability_zone       = data.aws_availability_zones.available.names[count.index]
  map_public_ip_on_launch = true

  tags = merge(local.common_tags, {
    Name = "${var.project_name}-public-${data.aws_availability_zones.available.names[count.index]}"
    Type = "public"
    "kubernetes.io/role/elb" = "1"  # For K8s ELB
  })
}

# Private Subnets (2 AZs, /20 each = 4,096 IPs per subnet)
resource "aws_subnet" "private" {
  count             = 2
  vpc_id            = aws_vpc.main.id
  cidr_block        = "10.0.${32 + count.index * 16}.0/20"
  availability_zone = data.aws_availability_zones.available.names[count.index]

  tags = merge(local.common_tags, {
    Name = "${var.project_name}-private-${data.aws_availability_zones.available.names[count.index]}"
    Type = "private"
    "kubernetes.io/role/internal-elb" = "1"  # For K8s internal ELB
  })
}

# COST SAVINGS: NAT Gateways commented out
# Uncomment for production HA setup (~$90/month for 2 gateways)
# resource "aws_nat_gateway" "main" {
#   count         = 2
#   allocation_id = aws_eip.nat[count.index].id
#   subnet_id     = aws_subnet.public[count.index].id
# 
#   tags = merge(local.common_tags, {
#     Name = "${var.project_name}-nat-${count.index + 1}"
#   })
# 
#   depends_on = [aws_internet_gateway.main]
# }

# Route Table for Public Subnets
resource "aws_route_table" "public" {
  vpc_id = aws_vpc.main.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.main.id
  }

  tags = merge(local.common_tags, {
    Name = "${var.project_name}-public-rt"
    Type = "public"
  })
}

# Route Tables for Private Subnets (one per AZ)
resource "aws_route_table" "private" {
  count  = 2
  vpc_id = aws_vpc.main.id

  # COST SAVINGS: Routes commented out since NAT gateways are disabled
  # Uncomment when using NAT gateways
  # route {
  #   cidr_block     = "0.0.0.0/0"
  #   nat_gateway_id = aws_nat_gateway.main[count.index].id
  # }
  
  # When using NAT instance instead:
  dynamic "route" {
    for_each = var.use_nat_instance ? [1] : []
    content {
      cidr_block           = "0.0.0.0/0"
      network_interface_id = aws_instance.nat_instance[0].primary_network_interface_id
    }
  }

  tags = merge(local.common_tags, {
    Name = "${var.project_name}-private-rt-${count.index + 1}"
    Type = "private"
  })
}

# Route Table Associations - Public
resource "aws_route_table_association" "public" {
  count          = 2
  subnet_id      = aws_subnet.public[count.index].id
  route_table_id = aws_route_table.public.id
}

# Route Table Associations - Private
resource "aws_route_table_association" "private" {
  count          = 2
  subnet_id      = aws_subnet.private[count.index].id
  route_table_id = aws_route_table.private[count.index].id
}

# VPC Endpoints for AWS services (cost optimization)
# S3 endpoint (Gateway type - free)
resource "aws_vpc_endpoint" "s3" {
  vpc_id            = aws_vpc.main.id
  service_name      = "com.amazonaws.${var.aws_region}.s3"
  vpc_endpoint_type = "Gateway"
  route_table_ids   = concat(
    [aws_route_table.public.id],
    aws_route_table.private[*].id
  )

  tags = merge(local.common_tags, {
    Name = "${var.project_name}-s3-endpoint"
  })
}

# COST SAVINGS: ECR endpoints cost ~$7.20/month each
# Uncomment for private ECR pulls without going through NAT
# resource "aws_vpc_endpoint" "ecr_api" {
#   vpc_id              = aws_vpc.main.id
#   service_name        = "com.amazonaws.${var.aws_region}.ecr.api"
#   vpc_endpoint_type   = "Interface"
#   subnet_ids          = aws_subnet.private[*].id
#   security_group_ids  = [aws_security_group.vpc_endpoints.id]
#   private_dns_enabled = true
# 
#   tags = merge(local.common_tags, {
#     Name = "${var.project_name}-ecr-api-endpoint"
#   })
# }
# 
# resource "aws_vpc_endpoint" "ecr_dkr" {
#   vpc_id              = aws_vpc.main.id
#   service_name        = "com.amazonaws.${var.aws_region}.ecr.dkr"
#   vpc_endpoint_type   = "Interface"
#   subnet_ids          = aws_subnet.private[*].id
#   security_group_ids  = [aws_security_group.vpc_endpoints.id]
#   private_dns_enabled = true
# 
#   tags = merge(local.common_tags, {
#     Name = "${var.project_name}-ecr-dkr-endpoint"
#   })
# }

# Security group for VPC endpoints
resource "aws_security_group" "vpc_endpoints" {
  name_prefix = "${var.project_name}-vpc-endpoints-"
  description = "Security group for VPC endpoints"
  vpc_id      = aws_vpc.main.id

  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = [aws_vpc.main.cidr_block]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(local.common_tags, {
    Name = "${var.project_name}-vpc-endpoints-sg"
  })
}

# Outputs
output "vpc_id" {
  value       = aws_vpc.main.id
  description = "ID of the VPC"
}

output "vpc_cidr" {
  value       = aws_vpc.main.cidr_block
  description = "CIDR block of the VPC"
}

output "public_subnet_ids" {
  value       = aws_subnet.public[*].id
  description = "IDs of public subnets"
}

output "private_subnet_ids" {
  value       = aws_subnet.private[*].id
  description = "IDs of private subnets"
}

# Commented out since NAT gateways are disabled for cost savings
# output "nat_gateway_ips" {
#   value       = aws_eip.nat[*].public_ip
#   description = "Elastic IPs of NAT gateways"
# }

# Summary of IP allocation:
# VPC CIDR: 10.0.0.0/16 (65,536 IPs total)
# 
# Public Subnets:
#   - 10.0.0.0/20   (AZ1: 4,096 IPs)
#   - 10.0.16.0/20  (AZ2: 4,096 IPs)
# 
# Private Subnets:
#   - 10.0.32.0/20  (AZ1: 4,096 IPs)
#   - 10.0.48.0/20  (AZ2: 4,096 IPs)
# 
# Reserved for future use:
#   - 10.0.64.0/18  (16,384 IPs)
#   - 10.0.128.0/17 (32,768 IPs)