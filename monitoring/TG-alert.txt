#!/bin/sh

#set -ex

#====================================================================================================================
# Maintainer : Umanath Pathak
# This script creates alerts for TargetGroup.
#====================================================================================================================

# Defining Variables

# Threshold
RequestCount_THRESHOLD="3000"
UnHealthyHostCount_THRESHOLD="0"
TargetResponseTime_THRESHOLD="1"

full_target_group_arn="arn:aws:elasticloadbalancing:us-east-1:211125736474:targetgroup/MyTargetGroup/366ef0cbad1af0cb"
REGION="us-east-1"
AccountName="MSP/MediaReady"
ARN_OF_SNS_TOPIC="arn:aws:sns:us-east-1:211125736474:3q3q.fifo"

# Extract the target group name from the ARN (including 'targetgroup')
TG_ID="targetgroup/$(echo "$full_target_group_arn" | cut -d'/' -f2-)"
echo "TG_ID= $TG_ID"

target_group_name="$(echo "$full_target_group_arn" | cut -d'/' -f2-)"
echo "target_group_name= $target_group_name"

# Get associated load balancer details
getLoadBalancerDetails() {
    # Get all load balancer ARNs
    load_balancer_arns=$(aws elbv2 describe-load-balancers --region "$REGION" --query 'LoadBalancers[*].LoadBalancerArn' --output text)

    # Loop through each load balancer ARN to find the associated one
    for lb_arn in $load_balancer_arns; do
        # Get all listeners for the current load balancer
        listeners=$(aws elbv2 describe-listeners --load-balancer-arn $lb_arn --region "$REGION" --query 'Listeners[*].ListenerArn' --output text)
        # Loop through each listener to check the DefaultActions and Rules
        for listener_arn in $listeners; do
            # Check if the target group ARN is associated with this listener's default actions
            associated_lb=$(aws elbv2 describe-listeners --listener-arn $listener_arn --region "$REGION" --query "Listeners[?DefaultActions[?TargetGroupArn=='$full_target_group_arn']].LoadBalancerArn" --output text)

            if [ -n "$associated_lb" ]; then
                # Print the associated load balancer ARN
                echo "Associated Load Balancer ARN: $associated_lb"
                # Describe the load balancer to get more details
                lb_details=$(aws elbv2 describe-load-balancers --load-balancer-arns $associated_lb --region "$REGION" --query 'LoadBalancers[*].LoadBalancerArn' --output text)
            fi

            # Get all rules for the current listener
            listener_rules=$(aws elbv2 describe-rules --listener-arn $listener_arn --region "$REGION" --query 'Rules[*].Actions[*].TargetGroupArn' --output text)

            for rule_tg_arn in $listener_rules; do
                if [ "$rule_tg_arn" == "$full_target_group_arn" ]; then
                    # Print the associated load balancer ARN
                    #echo "Associated Load Balancer ARN: $lb_arn"
                    # Describe the load balancer to get more details
                    lb_details=$(aws elbv2 describe-load-balancers --load-balancer-arns $lb_arn --region "$REGION" --query 'LoadBalancers[*].LoadBalancerArn' --output text)
                    echo "Load Balancer Details: $lb_details"
                fi
            done
        done
    done
}

# Call the function to get load balancer details
getLoadBalancerDetails

# Extract the desired part using cut
lb_name=$(echo "$lb_details" | cut -d'/' -f2-)
echo "Load Balancer Name= $lb_name"

# Fetch Service name from the TG
SVC=$(aws elbv2 describe-tags --resource-arns "$full_target_group_arn" --query "TagDescriptions[0].Tags[?Key=='ingress.k8s.aws/resource'].Value" --output text | cut -d':' -f1 | rev | cut -d'-' -f1 | rev)
echo "SVC Name= $SVC"

# Function to create RequestCount alarm
RequestCountAlarm() {
    aws cloudwatch put-metric-alarm \
    --alarm-name "${AccountName}/TG/${SVC}/${target_group_name}/RequestCount" \
    --alarm-description "Alarm when RequestCount is high" \
    --actions-enabled \
    --alarm-actions "${ARN_OF_SNS_TOPIC}" \
    --insufficient-data-actions \
    --treat-missing-data missing \
    --metric-name RequestCount \
    --namespace AWS/ApplicationELB \
    --statistic Sum \
    --dimensions Name=LoadBalancer,Value="${lb_name}" Name=TargetGroup,Value="${TG_ID}" \
    --period 300 \
    --region "${REGION}" \
    --threshold "${RequestCount_THRESHOLD}" \
    --comparison-operator GreaterThanThreshold \
    --datapoints-to-alarm 2 \
    --evaluation-periods 2

    echo "${AccountName}/TG/${SVC}/${target_group_name}/RequestCount"
}

# Function to create UnHealthyHost alarm
UnHealthyHostAlarm() {
    aws cloudwatch put-metric-alarm \
    --alarm-name "${AccountName}/TG/${SVC}/${target_group_name}/UnHealthyHostCount" \
    --alarm-description "Alarm when hosts are unhealthy" \
    --actions-enabled \
    --alarm-actions "${ARN_OF_SNS_TOPIC}" \
    --insufficient-data-actions "${ARN_OF_SNS_TOPIC}" \
    --treat-missing-data missing \
    --metric-name UnHealthyHostCount \
    --namespace AWS/ApplicationELB \
    --statistic Maximum \
    --dimensions Name=LoadBalancer,Value="${lb_name}" Name=TargetGroup,Value="${TG_ID}" \
    --period 60 \
    --region "${REGION}" \
    --threshold "${UnHealthyHostCount_THRESHOLD}" \
    --comparison-operator GreaterThanThreshold \
    --datapoints-to-alarm 1 \
    --evaluation-periods 1

    echo "${AccountName}/TG/${SVC}/${target_group_name}/UnHealthyHostCount"
}

# Function to create TargetResponseTime alarm
TargetResponseTimeAlarm() {
    aws cloudwatch put-metric-alarm \
    --alarm-name "${AccountName}/TG/${SVC}/${target_group_name}/TargetResponseTime" \
    --alarm-description "Alarm when TargetResponseTime is high" \
    --actions-enabled \
    --alarm-actions "${ARN_OF_SNS_TOPIC}" \
    --insufficient-data-actions \
    --treat-missing-data missing \
    --metric-name TargetResponseTime \
    --namespace AWS/ApplicationELB \
    --statistic Average \
    --dimensions Name=LoadBalancer,Value="${lb_name}" Name=TargetGroup,Value="${TG_ID}" \
    --period 300 \
    --region "${REGION}" \
    --threshold "${TargetResponseTime_THRESHOLD}" \
    --comparison-operator GreaterThanThreshold \
    --datapoints-to-alarm 2 \
    --evaluation-periods 2

    echo "${AccountName}/TG/${SVC}/${target_group_name}/TargetResponseTime"
}

# Call the alarm creation functions
RequestCountAlarm
UnHealthyHostAlarm
TargetResponseTimeAlarm