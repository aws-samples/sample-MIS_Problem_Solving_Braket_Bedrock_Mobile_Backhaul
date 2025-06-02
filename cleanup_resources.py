import boto3
import json
from dotenv import load_dotenv
import os
import time
import sys
import logging

# Function that implements exponential backoff
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


# Configure logging
logging.basicConfig(
       level=logging.INFO,
       format='%(asctime)s - %(levelname)s - %(message)s',
       filename='cleanup.log'
   )
   
# Load environment variables
load_dotenv(dotenv_path='env.local')

# Get region from environment variables
region_name = os.getenv('region_name')

# Initialize AWS clients
bedrock_agent = boto3.client(service_name='bedrock-agent', region_name=region_name)
iam = boto3.client('iam')

def confirm_deletion(resources):
       """Ask for user confirmation before deleting resources"""
       print("The following resources will be deleted:")
       for resource_type, resource_id in resources:
           print(f"- {resource_type}: {resource_id}")
           
       if os.getenv('CLEANUP_FORCE') == 'true':
           return True
           
       response = input("Do you want to proceed? (y/N): ").lower()
       return response == 'y'

def load_environment():
       load_dotenv(dotenv_path='.env.local')
       
       # Validate required variables
       required_vars = ['agentId', 'agentAliasId', 'role_name', 'region_name']
       missing_vars = [var for var in required_vars if not os.getenv(var)]
       
       if missing_vars:
           logging.info(f"Missing required environment variables: {', '.join(missing_vars)}")
           print(f"Missing required environment variables: {', '.join(missing_vars)}")
           return False
       return True

def validate_aws_credentials():
       try:
           sts = boto3.client('sts')
           identity = sts.get_caller_identity()
           logging.info(f"Using AWS credentials for account: {identity['Account']}")
           return True
       except Exception as e:
           logging.info(f"Error validating AWS credentials: {str(e)}")
           print(f"Error validating AWS credentials: {str(e)}")
           return False
       
def resource_exists(resource_type, resource_id):
       try:
           if resource_type == "agent":
               bedrock_agent.get_agent(agentId=resource_id)
           elif resource_type == "role":
               iam.get_role(RoleName=resource_id)
           return True
       except Exception:
           return False

def delete_agent_resources(agent_id, agent_alias_id):
 logging.info(f"Deleting agent alias {agent_alias_id}...")
 print(f"Deleting agent alias {agent_alias_id}...")
 

 if not resource_exists("agent", agent_id):
       logging.info(f"Agent  {agent_id} does not exist. Skipping.")
       print(f"Agent  {agent_id} does not exist. Skipping.")
 else:

    try:
        bedrock_agent.delete_agent_alias(
            agentId=agent_id,
            agentAliasId=agent_alias_id
        )
        
        # Wait for alias deletion using wait_for_status
        def check_alias_status():
            try:
                bedrock_agent.get_agent_alias(
                    agentId=agent_id,
                    agentAliasId=agent_alias_id
                )
                return "EXISTS"
            except bedrock_agent.exceptions.ResourceNotFoundException:
                return "DELETED"
        
        wait_for_status(check_alias_status, "DELETED", f"Agent Alias {agent_alias_id}")
            
    except Exception as e:
        logging.info(f"Error deleting agent alias: {str(e)}")
        print(f"Error deleting agent alias: {str(e)}")

    logging.info(f"Deleting agent {agent_id}...")
    print(f"Deleting agent {agent_id}...")
    try:
        bedrock_agent.delete_agent(agentId=agent_id)
        
        # Wait for agent deletion using wait_for_status
        def check_agent_status():
            try:
                bedrock_agent.get_agent(agentId=agent_id)
                return "EXISTS"
            except bedrock_agent.exceptions.ResourceNotFoundException:
                return "DELETED"
        
        wait_for_status(check_agent_status, "DELETED", f"Agent {agent_id}")
                
    except Exception as e:
        logging.info(f"Error deleting agent: {str(e)}")
        print(f"Error deleting agent: {str(e)}")

def delete_iam_resources(role_name):
   logging.info(f"Deleting IAM role and policies for {role_name}...")
   print(f"Deleting IAM role and policies for {role_name}...")

   if not resource_exists("role", role_name):
       logging.info(f"Role  {role_name} does not exist. Skipping.")
       print(f"Role  {role_name} does not exist. Skipping.")
   else:
       
     try:
        # List and delete inline policies
        policies = iam.list_role_policies(RoleName=role_name)
        for policy_name in policies['PolicyNames']:
            logging.info(f"Deleting inline policy {policy_name}")
            print(f"Deleting inline policy {policy_name}")
            iam.delete_role_policy(
                RoleName=role_name,
                PolicyName=policy_name
            )

        # Delete the role
        iam.delete_role(RoleName=role_name)
        logging.info(f"Successfully deleted role {role_name}")
        print(f"Successfully deleted role {role_name}")
        
     except Exception as e:
        logging.info(f"Error deleting IAM resources: {str(e)}")
        print(f"Error deleting IAM resources: {str(e)}")

def main():
    
    # Explicitly specify the path to your env.env file
    load_dotenv(dotenv_path='env.env')

    if not validate_aws_credentials():
       logging.info("Invalid AWS credentials. Exiting.")
       print("Invalid AWS credentials. Exiting.")
       sys.exit(1)
    
    if not load_environment():
       logging.info("Environment configuration incomplete. Exiting.")
       print("Environment configuration incomplete. Exiting.")
       sys.exit(1)

    # Get the agent ID and alias ID from  environment variables
    agent_id=os.getenv('agentId')  
    agent_alias_id = os.getenv('agentAliasId')
    role_name = os.getenv('role_name')

    resources_to_delete = [
       ("Agent Alias", agent_alias_id),
       ("Agent", agent_id),
       ("IAM Role", role_name)
   ]
   
    if not confirm_deletion(resources_to_delete):
       logging.info("Cleanup cancelled.")
       print("Cleanup cancelled.")
       sys.exit(0)
    # Delete Bedrock agent resources
    if agent_id and agent_alias_id:
        delete_agent_resources(agent_id, agent_alias_id)
    
    # Delete IAM resources
    if role_name:
        delete_iam_resources(role_name)

if __name__ == "__main__":
    main()   
