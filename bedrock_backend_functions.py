import boto3
import json
from dotenv import load_dotenv
import os
import base64
import io
from PIL import Image
from Prompts import *


import networkx as nx
import numpy as np
from scipy.optimize import minimize
from Quantum_API import quantum_simulator_execute



# libraries for agent

import matplotlib.pyplot as plt

import logging

from botocore.config import Config




# Explicitly specify the path to your env.env file
load_dotenv(dotenv_path='env.local')

region_name = os.getenv('region_name')   

if not region_name:
       logging.error("Missing region_name in environment variables")
       raise ValueError("AWS region not configured")

endpoint_url = os.getenv('bedrock_endpoint_url', f'https://bedrock-runtime.{region_name}.amazonaws.com')

aws_config = Config(
       connect_timeout=5,
       read_timeout=30,
       retries={'max_attempts': 3}
   )

# instantiating the Bedrock client, and passing in the CLI profile
try:
       boto3.setup_default_session(profile_name=os.getenv("profile_name"))
       bedrock = boto3.client('bedrock-runtime', region_name, endpoint_url=endpoint_url,config=aws_config)
       
except Exception as e:
        logging.error(f"Failed to initialize AWS client: {str(e)}")
        raise ValueError("Failed to initialize AWS client")

# Set up Bedrock Agent 
bedrock_agent = boto3.client(service_name = 'bedrock-agent', region_name = region_name)

# Set up runtime client to interact with it
bedrock_agent_runtime = boto3.client(service_name = 'bedrock-agent-runtime', region_name = region_name)

agentAliasId=os.getenv('agentAliasId')   
agentId=os.getenv('agentId') 

# # Specify the foundation model to use image analysis, is the same as the one being used in the agent as per .env file definition
foundationModel = os.getenv('foundationModel')  


#Agent invoke function

# Set up logging
logging.basicConfig(
       level=logging.INFO,
       format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
       filename='app_security.log'
   )


def process_image_to_graph(file_obj,sessionId):

    try:
     # Reset file position to beginning
     if hasattr(file_obj, 'seek'):
            file_obj.seek(0)

     image_analysis = image_to_text(file_obj, "")
     text,image_data = invoke_agent(f"{PROMPT_GENERATE_GRAPH} {image_analysis}", sessionId)
     return text,image_data
    except Exception as e:
           print(f"Error processing image: {str(e)}")
           return "Error processing image", None
   
   

def generate_atom_arrangement(sessionId):

    text,image_data = invoke_agent(f"{PROMPT_GENERATE_ATOM_ARRANGEMENT}", sessionId)
    return text,image_data     

def modify_network_graph(modify_text,sessionId):

    text,image_data = invoke_agent(f"Change previous graph modifiying nodes or connections using the following instructions: {modify_text}", sessionId)
    return text,image_data   

def modify_atom_arrangement(modify_text,sessionId):

    text,image_data = invoke_agent(f"{PROMPT_MODIFY_ATOM_ARRANGEMENT_GRAPH} {modify_text}", sessionId)
    return text,image_data   

def execute_quantum_algorythm(mode,sessionId):

    graph_array,image_blank = invoke_agent(f"{PROMPT_CREATE_INPUT_QUANTUM_EXEC_FUNCTION}",sessionId)
    result = quantum_simulator_execute(graph_array,mode)
    
    if mode=="simulator":
      text,image_data = process_quantum_results (result,sessionId) 
      return text,image_data
    else:
      return result      

def process_quantum_results (result,sessionId):
        
        
    
        text,image_data = invoke_agent(f"""use this dictionary {result} to draw again the network graph but use the letter to identify
                                                              the draw the color of the node, if letter is r draw the node red and if letter is g draw the node blue. for
                                                              example if [('rg', 2)] draw the node 0 red and node 1 blue """,sessionId)
                 
        return text,image_data   


def invoke_agent(inputText,sessionId,showTrace=True, endSession=False):
    
    generated_image = None  # Initialize image return value
    generated_text = "" # Initialize text return value

    try:

        
        response = bedrock_agent_runtime.invoke_agent(
            agentAliasId=agentAliasId,   # (string) – [REQUIRED] The alias of the agent to use.
            agentId=agentId,             # (string) – [REQUIRED] The unique identifier of the agent to use.
            sessionId=sessionId,         # (string) – [REQUIRED] The unique identifier of the session. Use the same value across requests to continue the same conversation.
            inputText=inputText,         # (string) - The prompt text to send the agent.
            endSession=endSession,       # (boolean) – Specifies whether to end the session with the agent or not.
            enableTrace=True,            # (boolean) – Specifies whether to turn on the trace or not to track the agent's reasoning process.
        )

        # The response of this operation contains an EventStream member. 
        event_stream = response["completion"]

        # When iterated the EventStream will yield events.
        for event in event_stream:

            # chunk contains a part of an agent response
            if 'chunk' in event:
                chunk = event['chunk']
                if 'bytes' in chunk:
                    text = chunk['bytes'].decode('utf-8')
                    print(f"Chunk: {text}")
                    generated_text = text
                else:
                    print("Chunk doesn't contain 'bytes'")

            # files contains intermediate response for code interpreter if any files have been generated.
            if 'files' in event:
                files = event['files']['files']
                for file in files:
                    name = file['name']
                    type = file['type']
                    bytes_data = file['bytes']
                    
                    # It the file is a PNG image then we can display it...
                    if type == 'image/png':
                        # Display PNG image using Matplotlib
                        
                        img = plt.imread(io.BytesIO(bytes_data))

                        # Create figure
                        fig, ax = plt.subplots(figsize=(10, 10))
                        ax.imshow(img)
                        ax.axis('off')
                        ax.set_title(name)
                
                        # Save figure to buffer
                        buf = io.BytesIO()
                        plt.savefig(buf, format='png', bbox_inches='tight')
                        buf.seek(0)
                        plt.close(fig)
                        
                        generated_image=buf
                        
                    else:
                        # Save other file types to local disk
                        with open(name, 'wb') as f:
                            f.write(bytes_data)
        
        return generated_text,generated_image  # Return the image data and text

    except Exception as e:
        print(f"Error: {e}")
        return "",None


def image_base64_encoder(image_name):
    """
    This function takes in a string that represent the path to the image that has been uploaded by the user and the function
    is used to encode the image to base64. The base64 string is then returned.
    :param image_name: This is the path to the image file that the user has uploaded.
    :return: A base64 string of the image that was uploaded.
    """
    # opening the image file that was uploaded by the user
    open_image = Image.open(image_name)
    # creating a BytesIO object to store the image in memory
    image_bytes = io.BytesIO()
    # saving the image to the BytesIO object
    open_image.save(image_bytes, format=open_image.format)
    # converting the BytesIO object to a base64 string and returning it
    image_bytes = image_bytes.getvalue()
    image_base64 = base64.b64encode(image_bytes).decode('utf-8')
    # getting the appropriate file type as claude 3 expects the file type to be presented
    file_type = f"image/{open_image.format.lower()}"
    # returning both the formatted file type string, along with the base64 encoded image
    return file_type, image_base64


def image_to_text(image_name, text) -> str:
    """
    This function is used to perform an image to text llm invocation against Claude 3. It can work with just an image and/or with
    text. If the user does not use any text, a default prompt will be passed in along with the system prompt as Claude 3 expects
    text in the text block of the prompt.
    :param image_name: This is the path to the image file that the user has uploaded.
    :param text: This is the text the user inserted in the text box on the frontend.
    :return: A natural language response giving a detailed analysis of the image that was uploaded or answering a specific
    question that the user asked along with the image.
    """
    # invoking the image_base64_encoder function to encode the image to base64 and get the file type string
    file_type, image_base64 = image_base64_encoder(image_name)
    # checking if the user inserted any text along with the image, if not, we set text to a default since claude expects
    # text in the text block of the prompt.
    if text == "":
        text = "Use the system prompt"
    # this is the primary prompt passed into Claude3 with the system prompt, user uploaded image in base64 and any
    # text the user inserted
    prompt = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 1000,
        "temperature": 0.5,
        "system": PROMPT_LLM_DIRECT_INVOCATION_IMAGE_PROCESSING,
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": file_type,
                            "data": image_base64
                        }
                    },
                    {
                        "type": "text",
                        "text": text
                    }
                ]
            }
        ]
    }
    # formatting the prompt as a json string
    json_prompt = json.dumps(prompt)
    # invoking Claude3, passing in our prompt
    response = bedrock.invoke_model(body=json_prompt, modelId=foundationModel,
                                    accept="application/json", contentType="application/json")
    # getting the response from Claude3 and parsing it to return to the end user
    response_body = json.loads(response.get('body').read())
    # the final string returned to the end user
    llm_output = response_body['content'][0]['text']
    # returning the final string to the end user
    return llm_output


