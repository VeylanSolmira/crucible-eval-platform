# Temporary Workaround for Green Updates

## Current State
We've updated the Terraform configuration so that:
- Both blue and green instances always exist (`for_each = toset(["blue", "green"])`)
- `lifecycle` blocks prevent updates to resources not in `enabled_deployment_colors`
- This allows `tofu apply -var='enabled_deployment_colors=["green"]'` to work properly

## HOWEVER
Since blue was previously managed by Terraform with the old configuration, the first apply will want to update blue to match the new structure.

## Temporary Workaround Until Blue is Updated

Use targeted applies to update only green resources:

```bash
# Update green instance and its dependencies
tofu apply \
  -target='aws_instance.eval_server["green"]' \
  -target='aws_eip.eval_server["green"]' \
  -target='aws_eip_association.eval_server["green"]' \
  -target='module.monitoring' \
  -target='aws_sns_topic.crucible_alerts' \
  -target='aws_sns_topic_subscription.crucible_alerts_email' \
  -target='aws_cloudwatch_log_group.crucible_docker' \
  -target='aws_cloudwatch_log_group.crucible_system' \
  -target='aws_ssm_parameter.cloudwatch_agent_config' \
  -target='aws_cloudwatch_metric_alarm.oom_alarm' \
  -target='aws_cloudwatch_metric_alarm.container_restart_alarm' \
  -target='aws_cloudwatch_metric_alarm.low_memory_alarm' \
  -target='aws_cloudwatch_metric_alarm.high_cpu_alarm' \
  -target='aws_cloudwatch_log_metric_filter.oom_kills' \
  -target='aws_cloudwatch_log_metric_filter.container_restarts' \
  -target='aws_cloudwatch_dashboard.crucible_monitoring'
```

## Once Blue is Ready to Update

When you're ready to update blue (during a maintenance window):

```bash
# This will update blue to match the new configuration
tofu apply
```

## After Both Are Updated

Once both environments have been updated with the new configuration, you can use the simple command:

```bash
# Update only green
tofu apply -var='enabled_deployment_colors=["green"]'

# Update only blue  
tofu apply -var='enabled_deployment_colors=["blue"]'

# Update both (default)
tofu apply
```

## Why This Works

The lifecycle blocks check if a color is in `enabled_deployment_colors`:
- If yes: Allow all changes
- If no: Ignore changes to user_data, ami, instance_type, tags

This prevents Terraform from updating infrastructure for colors not being deployed to.