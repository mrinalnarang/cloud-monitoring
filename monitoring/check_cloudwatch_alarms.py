import csv
import os
from typing import Callable, Dict, List

import boto3

REGION = os.getenv("AWS_REGION", "us-east-1")

cloudwatch = boto3.client("cloudwatch", region_name=REGION)
ec2 = boto3.client("ec2", region_name=REGION)
elbv2 = boto3.client("elbv2", region_name=REGION)
rds = boto3.client("rds", region_name=REGION)
elasticache = boto3.client("elasticache", region_name=REGION)
autoscaling = boto3.client("autoscaling", region_name=REGION)
lambda_client = boto3.client("lambda", region_name=REGION)

RESOURCE_METRICS = {
    "EC2": ["CPUUtilization", "DiskUsedPercent", "MemoryUsedPercent", "StatusCheckFailed"],
    "LoadBalancer": ["HTTPCode_ELB_4XX_Count", "HTTPCode_Target_5XX_Count", "RequestCount"],
    "TargetGroup": ["UnHealthyHostCount", "RequestCount", "TargetResponseTime"],
    "RDS": ["CPUUtilization", "DatabaseConnections", "FreeableMemory"],
    "ElasticCache": ["CPUUtilization", "CurrConnections", "FreeableMemory"],
    "AutoScalingGroup": ["Fail to launch EC2 instance"],
    "Lambda": ["Throttles", "Errors", "Invocations"],
}


def get_running_instances() -> List[str]:
    paginator = ec2.get_paginator("describe_instances")
    return [
        instance["InstanceId"]
        for page in paginator.paginate()
        for reservation in page["Reservations"]
        for instance in reservation["Instances"]
    ]


def get_load_balancers() -> List[str]:
    paginator = elbv2.get_paginator("describe_load_balancers")
    return [lb["LoadBalancerArn"] for page in paginator.paginate() for lb in page["LoadBalancers"]]


def get_target_groups() -> List[str]:
    paginator = elbv2.get_paginator("describe_target_groups")
    return [tg["TargetGroupArn"] for page in paginator.paginate() for tg in page["TargetGroups"]]


def get_rds_instances() -> List[str]:
    paginator = rds.get_paginator("describe_db_instances")
    return [db["DBInstanceIdentifier"] for page in paginator.paginate() for db in page["DBInstances"]]


def get_elasticache_clusters() -> List[str]:
    paginator = elasticache.get_paginator("describe_cache_clusters")
    return [cache["CacheClusterId"] for page in paginator.paginate() for cache in page["CacheClusters"]]


def get_auto_scaling_groups() -> List[str]:
    paginator = autoscaling.get_paginator("describe_auto_scaling_groups")
    return [asg["AutoScalingGroupName"] for page in paginator.paginate() for asg in page["AutoScalingGroups"]]


def get_lambda_functions() -> List[str]:
    paginator = lambda_client.get_paginator("list_functions")
    return [func["FunctionName"] for page in paginator.paginate() for func in page["Functions"]]


def get_existing_alarms() -> List[Dict[str, str]]:
    alarms: List[Dict[str, str]] = []
    paginator = cloudwatch.get_paginator("describe_alarms")
    for page in paginator.paginate():
        for alarm in page.get("MetricAlarms", []):
            dimensions = alarm.get("Dimensions", [])
            resource_dimension = dimensions[0] if dimensions else {"Name": "N/A", "Value": "N/A"}
            alarms.append(
                {
                    "AlarmName": alarm["AlarmName"],
                    "MetricName": alarm["MetricName"],
                    "ResourceID": resource_dimension["Value"],
                    "ResourceName": resource_dimension["Name"],
                    "State": alarm["StateValue"],
                }
            )
    return alarms


def check_metrics(alarms: List[Dict[str, str]]):
    results = []
    no_alarms = []

    resource_getters: Dict[str, Callable[[], List[str]]] = {
        "EC2": get_running_instances,
        "LoadBalancer": get_load_balancers,
        "TargetGroup": get_target_groups,
        "RDS": get_rds_instances,
        "ElasticCache": get_elasticache_clusters,
        "AutoScalingGroup": get_auto_scaling_groups,
        "Lambda": get_lambda_functions,
    }

    for resource_type, metrics in RESOURCE_METRICS.items():
        resources = resource_getters[resource_type]()
        for metric_name in metrics:
            for resource in resources:
                alarms_found = any(
                    alarm["MetricName"] == metric_name and alarm["ResourceID"] == resource for alarm in alarms
                )
                target = results if alarms_found else no_alarms
                target.append(
                    {
                        "ResourceType": resource_type,
                        "ResourceID": resource,
                        "MetricName": metric_name,
                        "Status": "Alarm Present" if alarms_found else "No Alarm",
                    }
                )

    return results, no_alarms


def write_to_csv(results, no_alarms) -> None:
    with open("cloudwatch_alarms_check.csv", "w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=["ResourceType", "ResourceID", "MetricName", "Status"])
        writer.writeheader()
        writer.writerows(results)
        writer.writerows(no_alarms)


def main() -> None:
    alarms = get_existing_alarms()
    results, no_alarms = check_metrics(alarms)
    write_to_csv(results, no_alarms)
    print("Report generated: cloudwatch_alarms_check.csv")


if __name__ == "__main__":
    main()
