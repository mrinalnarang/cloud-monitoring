import subprocess
from datetime import datetime
import boto3

# AWS SNS client
sns_client = boto3.client('sns', region_name='your-region')

# MySQL Login Command
MYSQL_LOGIN_COMMAND = "mysql -h database-1.cny42c2wiyon.us-east-1.rds.amazonaws.com -u admin -p'mrinal123'"

# SQL Commands
SQL_COMMAND_1 = "USE mrinal;"
SQL_QUERY = "SELECT * FROM mrinal1;"

# SFTP server details
SFTP_HOST = "serverip"
SFTP_USER = "username"
SFTP_PASSWORD = "password"

# Execute SQL commands and save output to CSV file
try:
    cmd = f"{MYSQL_LOGIN_COMMAND} -e \"{SQL_COMMAND_1}; {SQL_QUERY}\" | sed 's/\t/|/g'"
    output = subprocess.check_output(cmd, shell=True).decode().strip()

    # Generate CSV filename with current date (yyyymmdd)
    CURRENT_DATE = datetime.now().strftime("%Y%m%d")
    CSV_FILE = f"/root/OTT_AssetID_{CURRENT_DATE}.csv"

    # Save output to CSV file
    with open(CSV_FILE, "w") as f:
        f.write(output.replace("\t", "|"))

    print(f"CSV file saved at: {CSV_FILE}")
    print("Columns Separated with |")

    # Step-13: Upload the file to the FTP server
    try:
        # Write SFTP command to a file
        sftp_commands = f"""
        put {CSV_FILE} /path/on/server/OTT_AssetID_{CURRENT_DATE}.csv
        bye
        """
        with open("/tmp/sftp_commands.txt", "w") as f:
            f.write(sftp_commands)

        # Execute the SFTP command using subprocess
        sftp_cmd = f'echo "{SFTP_PASSWORD}" | sftp -oBatchMode=no -b /tmp/sftp_commands.txt {SFTP_USER}@{SFTP_HOST}'
        subprocess.check_output(sftp_cmd, shell=True)

        print(f"File successfully uploaded to /path/on/server/OTT_AssetID_{CURRENT_DATE}.csv")

    except subprocess.CalledProcessError as ftp_error:
        print(f"Failed to upload file: {ftp_error}")

except subprocess.CalledProcessError as e:
    # Wrong password exception handling
    error_output = e.output.decode().strip()
    if "Access denied for user" in error_output:
        # Send SNS notification
        sns_client.publish(
            TopicArn='your-sns-topic-arn',
            Subject='5AM activity wrong password',
            Message='There was an attempt to access the database with the wrong password at 5AM.'
        )
    else:
        # For other errors, print the error message
        print("Error:", error_output)
