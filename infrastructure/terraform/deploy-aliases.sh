#!/bin/bash
# Blue/Green deployment aliases for Terraform

# Deploy to Green only
alias deploy-green='tofu apply \
  -target="aws_instance.eval_server[\"green\"]" \
  -target="aws_eip.eval_server[\"green\"]" \
  -target="aws_eip_association.eval_server[\"green\"]" \
  -target="aws_security_group.eval_server_shared" \
  -target="aws_security_group.eval_server_color[\"green\"]" \
  -target="module.monitoring" \
  -target="aws_sns_topic.crucible_alerts" \
  -target="aws_cloudwatch_log_group.crucible_docker" \
  -target="aws_cloudwatch_log_group.crucible_system" \
  -target="aws_ssm_parameter.cloudwatch_agent_config" \
  -target="aws_cloudwatch_dashboard.crucible_monitoring"'

# Deploy to Blue only  
alias deploy-blue='tofu apply \
  -target="aws_instance.eval_server[\"blue\"]" \
  -target="aws_eip.eval_server[\"blue\"]" \
  -target="aws_eip_association.eval_server[\"blue\"]" \
  -target="aws_security_group.eval_server_shared" \
  -target="aws_security_group.eval_server_color[\"blue\"]" \
  -target="module.monitoring"'

# Switch traffic to Green
alias switch-to-green='tofu apply \
  -target="aws_route53_record.crucible_a" \
  -var="active_deployment_color=green"'

# Switch traffic to Blue  
alias switch-to-blue='tofu apply \
  -target="aws_route53_record.crucible_a" \
  -var="active_deployment_color=blue"'

# Update shared resources only
alias deploy-shared='tofu apply \
  -target="aws_security_group.eval_server_shared" \
  -target="module.monitoring" \
  -target="aws_ecr_repository.crucible_platform" \
  -target="aws_iam_role.eval_server"'

echo "Blue/Green deployment aliases loaded!"
echo "Commands:"
echo "  deploy-green    - Update green environment only"
echo "  deploy-blue     - Update blue environment only"  
echo "  switch-to-green - Point DNS to green"
echo "  switch-to-blue  - Point DNS to blue"
echo "  deploy-shared   - Update shared resources only"