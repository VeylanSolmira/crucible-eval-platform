# EC2 instance for running evaluation platform with gVisor

# Use data source to get latest Ubuntu AMI
data "aws_ami" "ubuntu" {
  most_recent = true
  owners      = ["099720109477"] # Canonical

  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-amd64-server-*"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}

# Security group for evaluation server
resource "aws_security_group" "eval_server" {
  name        = "crucible-eval-server-sg"
  description = "Security group for Crucible evaluation server"

  # SSH access (restricted to your IP)
  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = [var.allowed_ssh_ip]
  }

  # Platform web interface
  ingress {
    from_port   = 8000
    to_port     = 8000
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # Allow all outbound
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "crucible-eval-sg"
  }
}

# Key pair for SSH access
resource "aws_key_pair" "eval_server_key" {
  key_name   = "crucible-eval-key"
  public_key = "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIPhoQtkUCQ78PROjyf0tcZQjEZ/fBX1PkNCZoxWjJhRU metr-eval-platform"
}

# EC2 instance
resource "aws_instance" "eval_server" {
  ami           = data.aws_ami.ubuntu.id
  instance_type = "t2.micro" # Free tier eligible
  
  key_name               = aws_key_pair.eval_server_key.key_name
  vpc_security_group_ids = [aws_security_group.eval_server.id]

  # Increase root volume to have space for Docker images
  root_block_device {
    volume_size = 30 # GB, free tier includes 30GB
    volume_type = "gp3"
  }

  # User data script to install Docker and gVisor
  user_data = <<-EOF
    #!/bin/bash
    set -e
    
    # Update system
    apt-get update
    apt-get upgrade -y
    
    # Install Docker
    apt-get install -y \
      ca-certificates \
      curl \
      gnupg \
      lsb-release
    
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
    
    echo \
      "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu \
      $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null
    
    apt-get update
    apt-get install -y docker-ce docker-ce-cli containerd.io
    
    # Install gVisor
    curl -fsSL https://gvisor.dev/archive.key | apt-key add -
    add-apt-repository "deb https://storage.googleapis.com/gvisor/releases release main"
    apt-get update
    apt-get install -y runsc
    
    # Configure Docker to use runsc
    runsc install
    systemctl restart docker
    
    # Add ubuntu user to docker group
    usermod -aG docker ubuntu
    
    # Install Python 3.11
    apt-get install -y python3.11 python3.11-venv python3-pip
    
    # Create directory for the platform
    mkdir -p /home/ubuntu/crucible
    chown ubuntu:ubuntu /home/ubuntu/crucible
    
    # Install git
    apt-get install -y git
    
    # Create a marker file to indicate setup is complete
    touch /home/ubuntu/setup-complete
    chown ubuntu:ubuntu /home/ubuntu/setup-complete
  EOF

  tags = {
    Name = "crucible-eval-server"
    Purpose = "AI evaluation with gVisor"
  }
}

# Outputs
output "eval_server_public_ip" {
  value = aws_instance.eval_server.public_ip
  description = "Public IP of the evaluation server"
}

output "eval_server_public_dns" {
  value = aws_instance.eval_server.public_dns
  description = "Public DNS of the evaluation server"
}

output "ssh_command" {
  value = "ssh ubuntu@${aws_instance.eval_server.public_ip}"
  description = "SSH command to connect to the server"
}

output "platform_url" {
  value = "http://${aws_instance.eval_server.public_ip}:8000"
  description = "URL to access the evaluation platform"
}