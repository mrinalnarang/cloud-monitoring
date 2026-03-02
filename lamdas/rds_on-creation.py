import os
import boto3

CPU_UTILIZATION_THRESHOLD = 75
REPLICA_LAG_THRESHOLD = 1
DB_CONNECTIONS_THRESHOLD = 2500
FREE_STORAGE_SPACE_THRESHOLD = 5368709120
FREEABLE_MEMORY_THRESHOLD = 1073741824
REGION = os.getenv("AWS_REGION", "ap-south-1")


def lambda_handler(event, context):
    print(event)

    detail = event.get("detail", {})
    instance_identifier = detail.get("SourceIdentifier")

    if detail.get("Message") != "DB instance created" or not instance_identifier:
        print("Skipping event: not a DB creation event.")
        return

    rds_client = boto3.client("rds", region_name=REGION)
    desc_instance = rds_client.describe_db_instances(DBInstanceIdentifier=instance_identifier)

    db_instances = desc_instance.get("DBInstances", [])
    if not db_instances:
        print(f"No DB instances found for {instance_identifier}")
        return

    vpc_id = db_instances[0].get("DBSubnetGroup", {}).get("VpcId")
    if vpc_id != os.environ.get("VPC_ID"):
        print(f"Skipping instance {instance_identifier}: VPC mismatch ({vpc_id}).")
        return

    cloudwatch = boto3.client("cloudwatch", region_name=REGION)
    dimensions = [{"Name": "DBInstanceIdentifier", "Value": instance_identifier}]
    sns_arn = os.environ["SNS_TOPIC_ARN"]

    alarms = [
        {
            "name": f"aws-rds-{instance_identifier}-High-CPU-Utilization",
            "description": "CPU Usage >=75% for 15 minutes",
            "metric": "CPUUtilization",
            "threshold": CPU_UTILIZATION_THRESHOLD,
            "operator": "GreaterThanOrEqualToThreshold",
            "period": 300,
            "evaluation": 3,
        },
        {
            "name": f"aws-rds-{instance_identifier}-High-DB-Connections",
            "description": "High DB Connections > 2500",
            "metric": "DatabaseConnections",
            "threshold": DB_CONNECTIONS_THRESHOLD,
            "operator": "GreaterThanOrEqualToThreshold",
            "period": 300,
            "evaluation": 1,
        },
        {
            "name": f"aws-rds-{instance_identifier}-Low-Free-Storage-Space",
            "description": "DB Storage free space is lower than 5GB",
            "metric": "FreeStorageSpace",
            "threshold": FREE_STORAGE_SPACE_THRESHOLD,
            "operator": "LessThanOrEqualToThreshold",
            "period": 300,
            "evaluation": 1,
        },
        {
            "name": f"aws-rds-{instance_identifier}-Low-Freeable-Memory",
            "description": "DB free memory is lower than 1GB",
            "metric": "FreeableMemory",
            "threshold": FREEABLE_MEMORY_THRESHOLD,
            "operator": "LessThanOrEqualToThreshold",
            "period": 300,
            "evaluation": 1,
        },
        {
            "name": f"aws-rds-{instance_identifier}-High-Replica-Lag",
            "description": "DB replica lag is greater than 1 second",
            "metric": "ReplicaLag",
            "threshold": REPLICA_LAG_THRESHOLD,
            "operator": "GreaterThanOrEqualToThreshold",
            "period": 300,
            "evaluation": 1,
        },
    ]

    for index, alarm in enumerate(alarms, start=1):
        cloudwatch.put_metric_alarm(
            AlarmName=alarm["name"],
            AlarmDescription=alarm["description"],
            AlarmActions=[sns_arn],
            MetricName=alarm["metric"],
            Namespace="AWS/RDS",
            Statistic="Average",
            Dimensions=dimensions,
            Period=alarm["period"],
            EvaluationPeriods=alarm["evaluation"],
            Threshold=alarm["threshold"],
            ComparisonOperator=alarm["operator"],
        )
        print(f"Alarm {index} created: {alarm['name']}")
