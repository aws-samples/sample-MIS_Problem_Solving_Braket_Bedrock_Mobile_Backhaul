import boto3
import json
from dotenv import load_dotenv
import os


# libraries for agent
import time
import secrets  # For cryptographically secure random generation
#import random  # Removed insecure random
#import uuid
import string


# Explicitly specify the path to your env.env file
load_dotenv(dotenv_path='env.local')


# Waiter function
def wait_for_status(get_status_func, desired_status, resource_name, max_attempts=30):
    """
    Poll a resource until it reaches the desired status.
    
    Args:
        get_status_func: Function that returns the current status
        desired_status: The status we're waiting for
        resource_name: Name of the resource for logging
        max_attempts: Maximum number of polling attempts
    """
    print(f"Waiting for {resource_name} status of '{desired_status}'...")
    
    for attempt in range(max_attempts):
        current_status = get_status_func()
        print(f"{resource_name} status: {current_status}")
        
        if current_status == desired_status:
            return True
            
        # Use a backoff strategy instead of fixed sleep
        wait_time = min(2 * (1.5 ** attempt), 30)  # Exponential backoff capped at 30 seconds
        time.sleep(wait_time)
    
    raise TimeoutError(f"{resource_name} did not reach '{desired_status}' status within the allowed time")

# PROMPT LIBRARY

instruction = """You are an advanced AI agent with capabilities in code execution, chart generation, and complex data analysis. Your primary function is to assist users by solving problems and fulfilling requests through these capabilities. Here are your key attributes and instructions:

 Code Execution:

 You have access to a Python environment where you can write and execute code in real-time.
 When asked to perform calculations or data manipulations, always use this code execution capability to ensure accuracy.
 After executing code, report the exact output and explain the results.


 Data Analysis:

 You excel at complex data analysis tasks. This includes statistical analysis, data visualization, and machine learning applications.
 Approach data analysis tasks systematically: understand the problem, prepare the data, perform the analysis, and interpret the results.


 Problem-Solving Approach:

 When presented with a problem or request, break it down into steps.
 Clearly communicate your thought process and the steps you're taking.
 If a task requires multiple steps or tools, outline your approach before beginning.

 Transparency and Accuracy:

 Always be clear about what you're doing. If you're running code, say so. If you're generating an image, explain that.
 If you're unsure about something or if a task is beyond your capabilities, communicate this clearly.
 Do not present hypothetical results as actual outcomes. Only report real results from your code execution or image generation.

 Interaction Style:

 Be concise in simple queries but provide detailed explanations for complex tasks.
 Use technical language appropriately, but be prepared to explain concepts in simpler terms if asked.
 Proactively offer relevant information or alternative approaches that might be helpful.


 Continuous Improvement:

 After completing a task, ask if the user needs any clarification or has follow-up questions.
 Be receptive to feedback and adjust your approach accordingly.


 Remember, your goal is to provide accurate, helpful, and insightful assistance by leveraging your unique capabilities in code execution, image generation, and data analysis. Always strive to give the most practical and effective solution to the user's request."""


# Specify the foundation model and the region to use

foundationModel=os.getenv('foundationModel')  
region_name=os.getenv('region_name')


#Create Bedrock and Bedrock runtime clients
bedrock = boto3.client("bedrock", region_name=region_name)
br = boto3.client("bedrock-runtime", region_name=region_name)

# Set up Bedrock Agent and IAM clients
bedrock_agent = boto3.client(service_name = 'bedrock-agent', region_name = region_name)
iam = boto3.client('iam')


agentName = 'code-interpreter-test-agent'

# Define the agent's personality and behavior

# Generate a random suffix for unique naming using cryptographically secure random generation
randomSuffix = "".join(
    secrets.choice(string.ascii_uppercase + string.digits) for _ in range(5)
 )

print("Creating the IAM policy and role...")

# Define IAM trust policy
trustPolicy = {
     "Version": "2012-10-17",
     "Statement": [
         {
             "Effect": "Allow",
             "Principal": {
                 "Service": [
                    "bedrock.amazonaws.com",
                    "braket.amazonaws.com"
                ]
             },
             "Action": "sts:AssumeRole"
         }
     ]
}

# Define IAM policy for invoking the foundation model
# Define IAM policy for invoking the foundation model and Braket QuEra device
policy = {
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "bedrock:InvokeModel",
                "bedrock:CreateAgent",
                "bedrock:GetAgent",
                "bedrock-agent:*",
                "bedrock:CreateInferenceProfile",
                "bedrock:GetInferenceProfile",
                "bedrock:ListInferenceProfiles",
                "bedrock:DeleteInferenceProfile",
                "bedrock:TagResource",
                "bedrock:UntagResource",
                "bedrock:ListTagsForResource"
            ],
            "Resource": [
                f"arn:aws:bedrock:{region_name}::foundation-model/*",
                f"arn:aws:bedrock:{region_name}:*:*",
                f"arn:aws:bedrock:*:*:inference-profile/*",
                f"arn:aws:bedrock:*:*:application-inference-profile/*"
            ]
        },
        {
            "Effect": "Allow",
            "Action": [
                "braket:CreateQuantumTask",
                "braket:GetQuantumTask",
                "braket:CancelQuantumTask",
                "braket:SearchQuantumTasks",
                "braket:GetDevice"
            ],
            "Resource": [
                "arn:aws:braket:us-east-1::device/qpu/quera/Aquila"
            ]
        },
        {
            "Effect": "Allow",
            "Action": [
                "s3:CreateBucket",
                "s3:GetObject",
                "s3:PutObject",
                "s3:ListBucket"
            ],
            "Resource": [
                "arn:aws:s3:::amazon-braket-*",
                "arn:aws:s3:::amazon-braket-*/*"
            ]
        }
    ]
}


role_name = f"test-agent-{randomSuffix}"

# Create IAM role and attach policy
role = iam.create_role(
     RoleName=role_name,
     AssumeRolePolicyDocument = json.dumps(trustPolicy)
 )

iam.put_role_policy(
     RoleName=role_name,
     PolicyName = f"policy-test-agent-{randomSuffix}",
     PolicyDocument = json.dumps(policy)
 )

roleArn = role['Role']['Arn']

print(f"IAM Role: {roleArn[:13]}{'*' * 12}{roleArn[25:]}")

print("Creating the agent...")

# Create the inference_profile

try:
    response = bedrock_agent.create_agent(
         agentName=f"{agentName}-{randomSuffix}",
         foundationModel=foundationModel,
         instruction=instruction,
         agentResourceRoleArn=roleArn,
    )
    agentId = response['agent']['agentId']
except Exception as e:
    print(f"Error creating agent: {str(e)}")
    # Handle the error appropriately (e.g., exit the script or take alternative action)
    raise

print("Waiting as agent status is still 'CREATING'...")


wait_for_status(
    lambda: bedrock_agent.get_agent(agentId=agentId)['agent']['agentStatus'],
    'NOT_PREPARED',
    'Agent'
)

######################################### Configure code interpreter for the agent
response = bedrock_agent.create_agent_action_group(
    
     actionGroupName='CodeInterpreterAction',
     actionGroupState='ENABLED',
     agentId=agentId,
     agentVersion='DRAFT',

     parentActionGroupSignature='AMAZON.CodeInterpreter' # <-  To allow your agent to generate, 
                                                         #     run, and troubleshoot code when trying 
                                                         #     to complete a task, set this field to 
                                                         #     AMAZON.CodeInterpreter. 
                                                         #     You must leave the `description`, `apiSchema`, 
                                                         #     and `actionGroupExecutor` fields blank for 
                                                         #     this action group.
 )

actionGroupId = response['agentActionGroup']['actionGroupId']

print("Waiting for action group status of 'ENABLED'...")



wait_for_status(
    lambda: bedrock_agent.get_agent_action_group(
        agentId=agentId,
        actionGroupId=actionGroupId,
        agentVersion='DRAFT'
    )['agentActionGroup']['actionGroupState'],
    'ENABLED',
    'Action Group'
)




print("Preparing the agent...")

# Prepare the agent for use
response = bedrock_agent.prepare_agent(
     agentId=agentId
 )

print("Waiting for agent status of 'PREPARED'...")



wait_for_status(
    lambda: bedrock_agent.get_agent(agentId=agentId)['agent']['agentStatus'],
    'PREPARED',
    'Agent'
)

print("Creating an agent alias...")

# Create an alias for the agent
response = bedrock_agent.create_agent_alias(
     agentAliasName='test',
     agentId=agentId
 )

agentAliasId = response['agentAlias']['agentAliasId']

# Wait for agent alias to be prepared
#agentAliasStatus = ''
#while agentAliasStatus != 'PREPARED':
#     response = bedrock_agent.get_agent_alias(
#         agentId=agentId,
#         agentAliasId=agentAliasId
#     )
#     agentAliasStatus = response['agentAlias']['agentAliasStatus']
#     print(f"Agent alias status: {agentAliasStatus}")
#     time.sleep(2)

wait_for_status(
    lambda: bedrock_agent.get_agent_alias(
        agentId=agentId,
        agentAliasId=agentAliasId
    )['agentAlias']['agentAliasStatus'],
    'PREPARED',
    'Agent alias'
)
print('Done.\n')

print(f"Save this variables in your env.local file. agentId: {agentId}, agentAliasId: {agentAliasId}, role_name:{role_name}")


