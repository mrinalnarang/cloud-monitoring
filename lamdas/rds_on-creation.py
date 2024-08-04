import json
import boto3
import os

CPUUtilization_threshold=75
ReplicaLag_threshold=1
DBConnections_threshold=2500
FreeStorageSpace_threshold=5368709120 
FreeableMemory_threshold=1073741824  
region = 'ap-south-1' 

def lambda_handler(event, context):
    print(event)
    
    instanceIdentifier = event['detail']['SourceIdentifier']
    client = boto3.client('rds')
    desc_instance = client.describe_db_instances(
    DBInstanceIdentifier=instanceIdentifier,)
    
    for i in desc_instance['DBInstances']:
        data = i['DBSubnetGroup']
        for x,y in data.items():
            if x == 'VpcId':
                print(y)
                if y == os.environ['VPC_ID']:
                    if event['detail']['Message'] == 'DB instance created':

                        client = boto3.client('cloudwatch',region_name= region)
                        response = client.put_metric_alarm(
                        AlarmName= f"aws-rds-{event['detail']['SourceIdentifier']}-High-CPU-Utilization",
                        AlarmDescription= 'CPU Usage >=80% for 15 minutes',
                        AlarmActions=[
                            os.environ['SNS_TOPIC_ARN'],
                        ],
                        MetricName='CPUUtilization',
                        Namespace='AWS/RDS',
                        Statistic= 'Average',
                        Dimensions=[
                            {
                                'Name': 'DBInstanceIdentifier',
                                'Value': event['detail']['SourceIdentifier']
                            },
                        ],
                        Period=300,
                        EvaluationPeriods=3,
                        Threshold= CPUUtilization_threshold,
                        ComparisonOperator='GreaterThanOrEqualToThreshold',
                        )
                        print("alarm 1 created")
                        
                        response = client.put_metric_alarm(
                        AlarmName= f"aws-rds-{event['detail']['SourceIdentifier']}-High-DB-Connections",
                        AlarmDescription= 'High DB Connections > 100',
                        AlarmActions=[
                            os.environ['SNS_TOPIC_ARN'],
                        ],
                        MetricName='DatabaseConnections',
                        Namespace='AWS/RDS',
                        Statistic= 'Average',
                        Dimensions=[
                            {
                                'Name': 'DBInstanceIdentifier',
                                'Value': event['detail']['SourceIdentifier']
                            },
                        ],
                        Period=300,
                        EvaluationPeriods=1,
                        Threshold= DBConnections_threshold,
                        ComparisonOperator='GreaterThanOrEqualToThreshold',
                        )
                        print("alarm 2 created")
                        
                        response = client.put_metric_alarm(
                        AlarmName= f"aws-rds-{event['detail']['SourceIdentifier']}-Low-Free-Storage-Space",
                        AlarmDescription= 'DB Storage free space is lower than 5GB',
                        AlarmActions=[
                            os.environ['SNS_TOPIC_ARN'],
                        ],
                        MetricName='FreeStorageSpace',
                        Namespace='AWS/RDS',
                        Statistic= 'Average',
                        Dimensions=[
                            {
                                'Name': 'DBInstanceIdentifier',
                                'Value': event['detail']['SourceIdentifier']
                            },
                        ],
                        Period=300,
                        EvaluationPeriods=1,
                        Threshold= FreeStorageSpace_threshold,
                        ComparisonOperator='LessThanOrEqualToThreshold',
                        )
                        print("alarm 3 created")
                
                        response = client.put_metric_alarm(
                        AlarmName= f"aws-rds-{event['detail']['SourceIdentifier']}-Low-Freeable-Memory",
                        AlarmDescription= 'DB Free Memory is lower than 1GB',
                        AlarmActions=[
                            os.environ['SNS_TOPIC_ARN'],
                        ],
                        MetricName='FreeableMemory',
                        Namespace='AWS/RDS',
                        Statistic= 'Average',
                        Dimensions=[
                            {
                                'Name': 'DBInstanceIdentifier',
                                'Value': event['detail']['SourceIdentifier']
                            },
                        ],
                        Period=300,
                        EvaluationPeriods=1,
                        Threshold= FreeableMemory_threshold,
                        ComparisonOperator='LessThanOrEqualToThreshold',
                        )
                        print("alarm 4 created")
                
                        response = client.put_metric_alarm(
                        AlarmName= f"aws-rds-{event['detail']['SourceIdentifier']}-High-Replica-Lag",
                        AlarmDescription= 'DB replica lag is greater than 1seconds',
                        AlarmActions=[
                            os.environ['SNS_TOPIC_ARN'],
                        ],
                        MetricName='ReplicaLag',
                        Namespace='AWS/RDS',
                        Statistic= 'Average',
                        Dimensions=[
                            {
                                'Name': 'DBInstanceIdentifier',
                                'Value': event['detail']['SourceIdentifier']
                            },
                        ],
                        Period=300,
                        EvaluationPeriods=1,
                        Threshold= ReplicaLag_threshold,
                        ComparisonOperator='GreaterThanOrEqualToThreshold',
                        )
                        print("alarm 5 created")