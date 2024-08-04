import subprocess
import json
import csv
import boto3

# Initialize the CloudWatch and other clients with the region specified
cloudwatch = boto3.client('cloudwatch', region_name='us-east-1')
ec2 = boto3.client('ec2', region_name='us-east-1')
elbv2 = boto3.client('elbv2', region_name='us-east-1')
rds = boto3.client('rds', region_name='us-east-1')
elasticache = boto3.client('elasticache', region_name='us-east-1')
autoscaling = boto3.client('autoscaling', region_name='us-east-1')
lambda_client = boto3.client('lambda', region_name='us-east-1')

# Define the metrics for each resource type
resource_metrics = {
    'EC2': [
        'CPUUtilization', 'DiskUsedPercent', 'MemoryUsedPercent', 'StatusCheckFailed'
    ],
    'LoadBalancer': [
        'HTTPCode_ELB_4XX_Count', 'HTTPCode_Target_5XX_Count', 'RequestCount'
    ],
    'TargetGroup': [
        'UnHealthyHostCount', 'RequestCount', 'TargetResponseTime'
    ],
    'RDS': [
        'CPUUtilization', 'DatabaseConnections', 'FreeableMemory'
    ],
    'ElasticCache': [
        'CPUUtilization', 'CurrConnections', 'FreeableMemory'
    ],
    'AutoScalingGroup': [
        'Fail to launch EC2 instance'
    ],
    'Lambda': [
        'Throttles', 'Errors', 'Invocations'
    ]
}

# Function to execute the AWS CLI command and get existing alarms
def get_existing_alarms():
    command = (
        "aws cloudwatch describe-alarms --query "
        "\"MetricAlarms[*].{AlertName:AlarmName, MetricName:MetricName, ThresholdValue:Threshold, Priority:AlarmActions, ResourceID:Dimensions[0].Value, ResourceName:Dimensions[0].Name, State:StateValue}\" "
        "--output json"
    )
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    return json.loads(result.stdout)

# Functions to get resource data
def get_running_instances():
    response = ec2.describe_instances()
    instances = [instance['InstanceId'] for reservation in response['Reservations'] for instance in reservation['Instances']]
    return instances

def get_load_balancers():
    response = elbv2.describe_load_balancers()
    return [lb['LoadBalancerArn'] for lb in response['LoadBalancers']]

def get_target_groups():
    response = elbv2.describe_target_groups()
    return [tg['TargetGroupArn'] for tg in response['TargetGroups']]

def get_rds_instances():
    response = rds.describe_db_instances()
    return [db['DBInstanceIdentifier'] for db in response['DBInstances']]

def get_elasticache_clusters():
    response = elasticache.describe_cache_clusters()
    return [cache['CacheClusterId'] for cache in response['CacheClusters']]

def get_auto_scaling_groups():
    response = autoscaling.describe_auto_scaling_groups()
    return [asg['AutoScalingGroupName'] for asg in response['AutoScalingGroups']]

def get_lambda_functions():
    response = lambda_client.list_functions()
    return [func['FunctionName'] for func in response['Functions']]

# Function to check metrics against alarms
def check_metrics(alarms):
    no_alarms = []

    for resource_type, metrics in resource_metrics.items():
        if resource_type == 'EC2':
            resources = get_running_instances()
        elif resource_type == 'LoadBalancer':
            resources = get_load_balancers()
        elif resource_type == 'TargetGroup':
            resources = get_target_groups()
        elif resource_type == 'RDS':
            resources = get_rds_instances()
        elif resource_type == 'ElasticCache':
            resources = get_elasticache_clusters()
        elif resource_type == 'AutoScalingGroup':
            resources = get_auto_scaling_groups()
        elif resource_type == 'Lambda':
            resources = get_lambda_functions()

        for metric_name in metrics:
            for resource in resources:
                alarms_found = any(
                    alarm['MetricName'] == metric_name and
                    alarm['ResourceID'] == resource
                    for alarm in alarms
                )
                if not alarms_found:
                    no_alarms.append({
                        'ResourceType': resource_type,
                        'ResourceID': resource,
                        'MetricName': metric_name,
                        'Status': 'No Alarm'
                    })

    return no_alarms

# Function to write both alarms and missing alarms to a single CSV file
def write_combined_csv(alarms, no_alarms):
    with open('combined_alarms_report.csv', 'w', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=['Type', 'ResourceID', 'ResourceName', 'AlertName', 'MetricName', 'ThresholdValue', 'Priority', 'State', 'Status'])
        writer.writeheader()
        for alarm in alarms:
            writer.writerow({
                'Type': 'Existing Alarm',
                'ResourceID': alarm.get('ResourceID', 'N/A'),
                'ResourceName': alarm.get('ResourceName', 'N/A'),
                'AlertName': alarm.get('AlertName', 'N/A'),
                'MetricName': alarm.get('MetricName', 'N/A'),
                'ThresholdValue': alarm.get('ThresholdValue', 'N/A'),
                'Priority': ','.join(alarm.get('Priority', [])),
                'State': alarm.get('State', 'N/A'),
                'Status': 'Alarm Present'
            })
        for item in no_alarms:
            writer.writerow({
                'Type': 'Missing Alarm',
                'ResourceID': item.get('ResourceID', 'N/A'),
                'ResourceName': '',
                'AlertName': '',
                'MetricName': item.get('MetricName', 'N/A'),
                'ThresholdValue': '',
                'Priority': '',
                'State': '',
                'Status': item.get('Status', 'N/A')
            })

def main():
    alarms = get_existing_alarms()
    no_alarms = check_metrics(alarms)
    write_combined_csv(alarms, no_alarms)
    print("Combined report generated: combined_alarms_report.csv")

if __name__ == "__main__":
    main()
