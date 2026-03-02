import os
import subprocess
from datetime import datetime

import boto3

REGION = os.getenv("AWS_REGION", "us-east-1")
SNS_TOPIC_ARN = os.environ.get("SNS_TOPIC_ARN", "your-sns-topic-arn")

DB_HOST = os.environ.get("DB_HOST", "database-1.cny42c2wiyon.us-east-1.rds.amazonaws.com")
DB_USER = os.environ.get("DB_USER", "admin")
DB_PASSWORD = os.environ.get("DB_PASSWORD", "")
DB_NAME = os.environ.get("DB_NAME", "mrinal")
DB_QUERY = os.environ.get("DB_QUERY", "SELECT * FROM mrinal1;")

SFTP_HOST = os.environ.get("SFTP_HOST", "serverip")
SFTP_USER = os.environ.get("SFTP_USER", "username")
SFTP_PASSWORD = os.environ.get("SFTP_PASSWORD", "password")
SFTP_DEST_PATH = os.environ.get("SFTP_DEST_PATH", "/path/on/server")

sns_client = boto3.client("sns", region_name=REGION)


def main() -> None:
    try:
        mysql_command = (
            f"mysql -h {DB_HOST} -u {DB_USER} -p'{DB_PASSWORD}' "
            f"-e \"USE {DB_NAME}; {DB_QUERY}\""
        )
        cmd = f"{mysql_command} | sed 's/\t/|/g'"
        output = subprocess.check_output(cmd, shell=True, text=True).strip()

        current_date = datetime.now().strftime("%Y%m%d")
        csv_file = f"/tmp/OTT_AssetID_{current_date}.csv"
        with open(csv_file, "w", encoding="utf-8") as file:
            file.write(output)

        print(f"CSV file saved at: {csv_file}")

        sftp_commands_path = "/tmp/sftp_commands.txt"
        target_file = f"{SFTP_DEST_PATH}/OTT_AssetID_{current_date}.csv"
        with open(sftp_commands_path, "w", encoding="utf-8") as file:
            file.write(f"put {csv_file} {target_file}\nbye\n")

        sftp_cmd = (
            f'echo "{SFTP_PASSWORD}" | '
            f"sftp -oBatchMode=no -b {sftp_commands_path} {SFTP_USER}@{SFTP_HOST}"
        )
        subprocess.check_output(sftp_cmd, shell=True)
        print(f"File successfully uploaded to {target_file}")

    except subprocess.CalledProcessError as error:
        error_output = (error.output or "").strip()
        if "Access denied for user" in error_output:
            sns_client.publish(
                TopicArn=SNS_TOPIC_ARN,
                Subject="5AM activity wrong password",
                Message="There was an attempt to access the database with the wrong password at 5AM.",
            )
        else:
            print("Error:", error_output)


if __name__ == "__main__":
    main()
