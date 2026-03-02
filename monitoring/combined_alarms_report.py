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


def get_existing_alarms() -> List[Dict[str, str]]:
    alarms = []
    paginator = cloudwatch.get_paginator("describe_alarms")
    for page in paginator.paginate():
        for alarm in page.get("MetricAlarms", []):
            dimensions = alarm.get("Dimensions", [])
            resource_dimension = dimensions[0] if dimensions else {"Name": "N/A", "Value": "N/A"}
            alarms.append(
                {
                    "AlertName": alarm.get("AlarmName", "N/A"),
                    "MetricName": alarm.get("MetricName", "N/A"),
                    "ThresholdValue": alarm.get("Threshold", "N/A"),
                    "Priority": alarm.get("AlarmActions", []),
                    "ResourceID": resource_dimension["Value"],
                    "ResourceName": resource_dimension["Name"],
                    "State": alarm.get("StateValue", "N/A"),
                }
            )
    return alarms


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


def check_metrics(alarms: List[Dict[str, str]]) -> List[Dict[str, str]]:
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
                if not any(alarm["MetricName"] == metric_name and alarm["ResourceID"] == resource for alarm in alarms):
                    no_alarms.append(
                        {
                            "ResourceType": resource_type,
                            "ResourceID": resource,
                            "MetricName": metric_name,
                            "Status": "No Alarm",
                        }
                    )

    return no_alarms


def write_combined_csv(alarms, no_alarms) -> None:
    with open("combined_alarms_report.csv", "w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=[
                "Type",
                "ResourceID",
                "ResourceName",
                "AlertName",
                "MetricName",
                "ThresholdValue",
                "Priority",
                "State",
                "Status",
            ],
        )
        writer.writeheader()
        for alarm in alarms:
            writer.writerow(
                {
                    "Type": "Existing Alarm",
                    "ResourceID": alarm.get("ResourceID", "N/A"),
                    "ResourceName": alarm.get("ResourceName", "N/A"),
                    "AlertName": alarm.get("AlertName", "N/A"),
                    "MetricName": alarm.get("MetricName", "N/A"),
                    "ThresholdValue": alarm.get("ThresholdValue", "N/A"),
                    "Priority": ",".join(alarm.get("Priority", [])),
                    "State": alarm.get("State", "N/A"),
                    "Status": "Alarm Present",
                }
            )
        for item in no_alarms:
            writer.writerow(
                {
                    "Type": "Missing Alarm",
                    "ResourceID": item.get("ResourceID", "N/A"),
                    "ResourceName": "",
                    "AlertName": "",
                    "MetricName": item.get("MetricName", "N/A"),
                    "ThresholdValue": "",
                    "Priority": "",
                    "State": "",
                    "Status": item.get("Status", "N/A"),
                }
            )


def main() -> None:
    alarms = get_existing_alarms()
    no_alarms = check_metrics(alarms)
    write_combined_csv(alarms, no_alarms)
    print("Combined report generated: combined_alarms_report.csv")


if __name__ == "__main__":
    main()
