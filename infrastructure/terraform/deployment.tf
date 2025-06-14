# # Automated deployment using Terraform
# # COMMENTED OUT: We're going with manual deployment first, then GitHub Actions
# # This shows what NOT to do - mixing infrastructure and application deployment
# 
# # Build and upload package after S3 bucket is created
# resource "null_resource" "deploy_package" {
#   # Triggers on any code change
#   triggers = {
#     always_run = timestamp()
#     # Or use file hash for smarter updates:
#     # code_hash = filemd5("${path.module}/../../app.py")
#   }
# 
#   # Dependencies
#   depends_on = [
#     aws_s3_bucket.deployment,
#     aws_s3_bucket_versioning.deployment
#   ]
# 
#   # Build and upload package
#   provisioner "local-exec" {
#     command = <<-EOT
#       cd ${path.module}/../..
#       
#       # Create deployment package
#       TIMESTAMP=$(date +%Y%m%d-%H%M%S)
#       PACKAGE_NAME="crucible-platform-$${TIMESTAMP}.tar.gz"
#       
#       echo "📦 Building deployment package: $${PACKAGE_NAME}"
#       tar -czf "/tmp/$${PACKAGE_NAME}" \
#         --exclude='.git' \
#         --exclude='__pycache__' \
#         --exclude='*.pyc' \
#         --exclude='.env' \
#         --exclude='venv' \
#         --exclude='.pytest_cache' \
#         --exclude='logs' \
#         --exclude='storage/*' \
#         --exclude='*.log' \
#         --exclude='infrastructure' \
#         --exclude='docs' \
#         .
#       
#       # Upload to S3
#       echo "⬆️  Uploading to S3..."
#       aws s3 cp "/tmp/$${PACKAGE_NAME}" "s3://${aws_s3_bucket.deployment.id}/$${PACKAGE_NAME}"
#       
#       # Update latest pointer
#       aws s3 cp "/tmp/$${PACKAGE_NAME}" "s3://${aws_s3_bucket.deployment.id}/latest.tar.gz"
#       
#       # Store package name for EC2 to use
#       echo "$${PACKAGE_NAME}" > /tmp/deployed-version.txt
#       aws s3 cp /tmp/deployed-version.txt "s3://${aws_s3_bucket.deployment.id}/deployed-version.txt"
#       
#       # Cleanup
#       rm -f "/tmp/$${PACKAGE_NAME}" /tmp/deployed-version.txt
#       
#       echo "✅ Package uploaded successfully"
#     EOT
#   }
# }
# 
# # Option 1: Use Systems Manager to update running instances
# resource "null_resource" "update_ec2" {
#   # Only run after package is deployed
#   depends_on = [
#     null_resource.deploy_package,
#     aws_instance.eval_server
#   ]
#   
#   # Triggers when package updates
#   triggers = {
#     deployment = null_resource.deploy_package.id
#   }
# 
#   # Wait for instance to be ready
#   provisioner "local-exec" {
#     command = <<-EOT
#       echo "⏳ Waiting for EC2 instance to be ready..."
#       sleep 30
#       
#       # Check if instance has Systems Manager agent
#       INSTANCE_ID="${aws_instance.eval_server.id}"
#       
#       # Try to update via Systems Manager
#       aws ssm send-command \
#         --instance-ids "$${INSTANCE_ID}" \
#         --document-name "AWS-RunShellScript" \
#         --parameters 'commands=[
#           "cd /home/ubuntu",
#           "aws s3 cp s3://${aws_s3_bucket.deployment.id}/latest.tar.gz crucible-latest.tar.gz",
#           "rm -rf crucible-new && mkdir crucible-new",
#           "tar -xzf crucible-latest.tar.gz -C crucible-new",
#           "[ -d crucible ] && mv crucible crucible-old",
#           "mv crucible-new crucible",
#           "sudo systemctl restart crucible-platform"
#         ]' \
#         --output text \
#         --query "Command.CommandId" || echo "⚠️  SSM not available, manual update required"
#     EOT
#   }
# }
# 
# # Alternative: Output deployment instructions
# output "deployment_status" {
#   value = <<-EOT
#     
#     🚀 Deployment Status:
#     - Infrastructure: ✅ Created
#     - Code Package: ✅ Uploaded to S3
#     - EC2 Update: ${null_resource.update_ec2.id != "" ? "✅ Triggered" : "⏳ Manual update required"}
#     
#     To manually update EC2:
#     ssh ubuntu@${aws_instance.eval_server.public_ip} 'cd /home/ubuntu && aws s3 cp s3://${aws_s3_bucket.deployment.id}/latest.tar.gz . && tar -xzf latest.tar.gz && sudo systemctl restart crucible-platform'
#     
#     Access via SSH tunnel:
#     ssh -L 8080:localhost:8080 ubuntu@${aws_instance.eval_server.public_ip}
#     Then browse to: http://localhost:8080
#   EOT
#   
#   depends_on = [null_resource.update_ec2]
# }