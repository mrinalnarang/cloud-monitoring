import boto3
import csv

# Initialize the CloudWatch and EC2 clients with the region specified
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

def get_running_instances():
    response = ec2.describe_instances()
    instances = []
    for reservation in response['Reservations']:
        for instance in reservation['Instances']:
            instances.append(instance['InstanceId'])
    return instances

def get_load_balancers():
    response = elbv2.describe_load_balancers()
    load_balancers = [lb['LoadBalancerArn'] for lb in response['LoadBalancers']]
    return load_balancers

def get_target_groups():
    response = elbv2.describe_target_groups()
    target_groups = [tg['TargetGroupArn'] for tg in response['TargetGroups']]
    return target_groups

def get_rds_instances():
    response = rds.describe_db_instances()
    rds_instances = [db['DBInstanceIdentifier'] for db in response['DBInstances']]
    return rds_instances

def get_elasticache_clusters():
    response = elasticache.describe_cache_clusters()
    elasticache_clusters = [cache['CacheClusterId'] for cache in response['CacheClusters']]
    return elasticache_clusters

def get_auto_scaling_groups():
    response = autoscaling.describe_auto_scaling_groups()
    auto_scaling_groups = [asg['AutoScalingGroupName'] for asg in response['AutoScalingGroups']]
    return auto_scaling_groups

def get_lambda_functions():
    response = lambda_client.list_functions()
    lambda_functions = [func['FunctionName'] for func in response['Functions']]
    return lambda_functions

def get_existing_alarms():
    alarms = []
    paginator = cloudwatch.get_paginator('describe_alarms')
    for page in paginator.paginate():
        for alarm in page['MetricAlarms']:
            alarms.append({
                'AlarmName': alarm['AlarmName'],
                'MetricName': alarm['MetricName'],
                'ResourceID': alarm['Dimensions'][0]['Value'],
                'ResourceName': alarm['Dimensions'][0]['Name'],
                'State': alarm['StateValue']
            })
    return alarms

def check_metrics(alarms):
    results = []
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
                if alarms_found:
                    results.append({
                        'ResourceType': resource_type,
                        'ResourceID': resource,
                        'MetricName': metric_name,
                        'Status': 'Alarm Present'
                    })
                else:
                    no_alarms.append({
                        'ResourceType': resource_type,
                        'ResourceID': resource,
                        'MetricName': metric_name,
                        'Status': 'No Alarm'
                    })

    return results, no_alarms

def write_to_csv(results, no_alarms):
    with open('cloudwatch_alarms_check.csv', 'w', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=['ResourceType', 'ResourceID', 'MetricName', 'Status'])
        writer.writeheader()
        writer.writerows(results)
        writer.writerows(no_alarms)

def main():
    alarms = get_existing_alarms()
    results, no_alarms = check_metrics(alarms)
    write_to_csv(results, no_alarms)
    print("Report generated: cloudwatch_alarms_check.csv")

if __name__ == "__main__":
    main()
