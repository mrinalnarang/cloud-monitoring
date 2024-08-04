import boto3
import json
sns_client=boto3.client("sns")
ec2=boto3.client('ec2',region_name='ap-south-1')

arn='arn:aws:sns:ap-south-1:281176377529:tatasky-production-alarm'
def lambda_handler(event, context):
    count=0
    sgs = ec2.describe_security_groups()
    email_text= "";
    for i in sgs['SecurityGroups']:
        security_groups = i.get('GroupId')
        security_groups_desc=i['Description']
        group_text="Security group - "+security_groups_desc+" - "+security_groups+ " is open for public for port(s) : ";
        print(group_text)
        openPorts=False;
        allowed_sg=['sg-03e11c2a4bc9d3144','sg-09683e405d79018f3','sg-09b66c61b3160c552','sg-0e3dec4de591d1287']
        allowed_port = ['80' , '443' , '3','1194', '16050', '11342', '18942', '16719', '19575']
        for j in i['IpPermissions']:
            from_port = j.get('FromPort')
            if str(from_port) in allowed_port :
                continue;
            if security_groups in allowed_sg :
                continue;
            to_port = j.get('ToPort')
            for cidr in j['IpRanges']:
                     if  cidr['CidrIp'] == '0.0.0.0/0':
                          group_text = group_text + str(from_port)+ ",";
                          openPorts = True;
                          count=count+1

        if openPorts == True:
            group_text = group_text.rstrip(',')
            email_text = email_text + "\n" + group_text;
    if count == 0:        
                
      exit;
    else : 
      response = sns_client.publish(TargetArn=arn,Message=json.dumps({'default': email_text}),MessageStructure='json')
                          
                          
#
 #   Initialization:
  #      sns_client and ec2 are initialized using the boto3 library to interact with Amazon SNS and EC2 services, respectively. The SNS topic ARN arn is specified to send notifications.

  #  Lambda Handler Function:
   #     The lambda_handler function starts by setting count to 0, which will track the number of security groups with open ports.
    #    It retrieves all security groups in the specified region (ap-south-1) using the describe_security_groups() method.

 #   Iterating Through Security Groups:
  #      For each security group (i) in the response:
   #         The security group's ID and description are fetched.
    #        A base text (group_text) is created to describe the security group and any open ports it has.
    #       A flag openPorts is set to False initially, indicating whether any open ports are found.
     #       Two lists, allowed_sg and allowed_port, specify the security groups and ports that are allowed to be open to the public.

   # Checking IP Permissions:
    
#    The function iterates through the inbound rules (IpPermissions) of the security group.
 #       For each rule (j), it checks the FromPort and ToPort values:
  #          If FromPort matches an allowed port or the security group ID matches an allowed security group, the function skips the check.
   #     It then checks the IpRanges in each rule:
    #        If any range is set to 0.0.0.0/0 (which means the port is open to the entire internet), and the port is not in the allowed_port list, the port number is appended to group_text, and openPorts is set to True.
    #      The count is incremented by 1 for each such open port found.

    #Sending Notification:
     #   If no open ports are found (count == 0), the function exits without taking further action.
      #  If open ports are found (openPorts == True), the group_text is added to email_text.
       # The function then sends a notification with email_text as the message body using the sns_client.publish() method. The message structure is specified as JSON.

#The function is essentially auditing security groups for any configurations that might expose services to the public internet without proper restrictions, potentially indicating a security risk. 