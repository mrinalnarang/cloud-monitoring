import json
import os

import boto3

REGION = os.getenv("AWS_REGION", "ap-south-1")
SNS_TOPIC_ARN = os.getenv("SNS_TOPIC_ARN", "arn:aws:sns:ap-south-1:281176377529:tatasky-production-alarm")

ALLOWED_SG = {
    "sg-03e11c2a4bc9d3144",
    "sg-09683e405d79018f3",
    "sg-09b66c61b3160c552",
    "sg-0e3dec4de591d1287",
}
ALLOWED_PORTS = {"80", "443", "3", "1194", "16050", "11342", "18942", "16719", "19575"}

sns_client = boto3.client("sns", region_name=REGION)
ec2 = boto3.client("ec2", region_name=REGION)


def lambda_handler(event, context):
    findings = []
    sgs = ec2.describe_security_groups()

    for group in sgs.get("SecurityGroups", []):
        group_id = group.get("GroupId", "unknown")
        group_desc = group.get("Description", "N/A")

        if group_id in ALLOWED_SG:
            continue

        open_ports = []
        for permission in group.get("IpPermissions", []):
            from_port = permission.get("FromPort")
            if from_port is None or str(from_port) in ALLOWED_PORTS:
                continue

            if any(ip_range.get("CidrIp") == "0.0.0.0/0" for ip_range in permission.get("IpRanges", [])):
                open_ports.append(str(from_port))

        if open_ports:
            findings.append(
                f"Security group - {group_desc} - {group_id} is open for public for port(s): {','.join(open_ports)}"
            )

    if not findings:
        print("No non-approved public security-group ports detected.")
        return {"message": "No findings"}

    email_text = "\n".join(findings)
    sns_client.publish(
        TargetArn=SNS_TOPIC_ARN,
        Message=json.dumps({"default": email_text}),
        MessageStructure="json",
    )
    return {"message": "Notification sent", "findings_count": len(findings)}
