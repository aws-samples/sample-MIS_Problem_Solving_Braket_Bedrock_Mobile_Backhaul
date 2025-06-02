import streamlit as st
from pathlib import Path
import os
from dotenv import load_dotenv
from bedrock_backend_functions import process_quantum_results,execute_quantum_algorythm,process_image_to_graph,generate_atom_arrangement,modify_network_graph,modify_atom_arrangement
from Quantum_API import quantum_task_status,quantum_task_get_result
import uuid
import time
import re
from io import BytesIO
from PIL import Image
import hashlib

from secure_file_handler import validate_and_store_file, store_generated_image, get_file_as_bytesio, cleanup_all_files
import atexit

import secrets

import boto3
from botocore.config import Config
import logging




# Load environment variables
load_dotenv(dotenv_path='env.local')

# Configure AWS with minimal permissions and timeout
aws_config = Config(
    connect_timeout=5,
    retries={'max_attempts': 3},
    read_timeout=10
)

# Function to get AWS clients with proper error handling
def get_aws_client(service_name):
    try:
        return boto3.client(
            service_name,
            config=aws_config,
            region_name=os.getenv('region_name')
        )
    except Exception as e:
        logging.error(f"Failed to initialize AWS client: {str(e)}")
        st.error("Failed to connect to AWS services. Please check your credentials.")
        return None

# Rate Limiting
class RateLimiter:
    def __init__(self, max_calls, time_frame):
        self.max_calls = max_calls
        self.time_frame = time_frame  # in seconds
        self.calls = []
        
    def is_allowed(self):
        now = time.time()
        # Remove old calls
        self.calls = [call_time for call_time in self.calls if call_time > now - self.time_frame]
        
        # Check if under limit
        if len(self.calls) < self.max_calls:
            self.calls.append(now)
            return True
        return False

# Create rate limiters
if 'bedrock_limiter' not in st.session_state:
    st.session_state.bedrock_limiter = RateLimiter(max_calls=10, time_frame=60)  # 10 calls per minute
if 'quantum_limiter' not in st.session_state:
    st.session_state.quantum_limiter = RateLimiter(max_calls=5, time_frame=3600)  # 5 calls per hour

# Register temporal file cleanup on application exit
atexit.register(cleanup_all_files)

# constants for file validation
MAX_FILE_SIZE_MB = 5  # 5MB max file size
ALLOWED_MIME_TYPES = ["image/png", "image/jpeg", "image/jpg"]
MAX_TEXT_LENGTH = 500  # Maximum length for text inputs
   

# Function to sanitize text inputs
def sanitize_text_input(text):
    """
    Sanitizes text input to prevent injection attacks
    """
    if text is None:
        return ""
        
    # Limit length
    text = text[:MAX_TEXT_LENGTH]
    
    # Remove potentially dangerous characters
    # This is a basic example - adjust based on your specific needs
    text = re.sub(r'[^\w\s.,;:!?()-]', '', text)
    
    return text



# title of the streamlit app
st.title(f""":rainbow[Solving MIS problem using Amazon Bedrock and Amazon Braket]""")
# directions on what can be done with this streamlit app
st.header(f"""Directions to use this application:
1. Upload an image
2. Check if the nodes and edges has been correctly identified in a graph, if not ask for missing data and generate again the graph.
3. Generate an Atom Arrangement and check it, if is not correct tell where is the problem and create it again.
4. Execute algorithm on a local Quantum Simulator and check the results 
5. Execute algorithm on a Quantum Device using AWS Braket and check the results 
""", divider='rainbow')

# Initialize session state for secure file storage
if 'secure_files' not in st.session_state:
    st.session_state.secure_files = {}

#Store different button click state
if 'result_process_image' not in st.session_state:
    st.session_state.resultProcessImage = False  
if 'result_graph_ok' not in st.session_state:
    st.session_state.resultGraphOK = False   
if 'result_graph_nok' not in st.session_state:
    st.session_state.resultGraphNOK = False   

# Store uploaded file state


if 'generated_graph' not in st.session_state:
    st.session_state.generated_graph = None

if 'generated_completion' not in st.session_state:
    st.session_state.generated_completion = ""

if 'generated_atom_arrangement' not in st.session_state:
    st.session_state.generated_atom_arrangement = None

if 'generated_mis_graph' not in st.session_state:
    st.session_state.generated_mis_graph = None   


if 'generated_mis_qera_graph' not in st.session_state:
    st.session_state.generated_mis_qera_graph = None   
                
if 'sessionId' not in st.session_state:
    # Generate a secure random token with additional entropy
    random_bytes = secrets.token_bytes(32)
    session_id = uuid.UUID(bytes=random_bytes[:16])
    st.session_state.sessionId = str(session_id)
    st.session_state.session_created = time.time()

    # Add session expiration check
    SESSION_TIMEOUT_SECONDS = 3600  # 1 hour
    if 'session_created' in st.session_state:
        if time.time() - st.session_state.session_created > SESSION_TIMEOUT_SECONDS:
            # Reset session
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.warning("Your session has expired. Please start again.")
            st.stop()


if 'generated_graph_nok' not in st.session_state:
    st.session_state.generated_graph_nok = False

if 'generated_atom_nok' not in st.session_state:
    st.session_state.generated_atom_nok = False

if 'generated_graph_ok' not in st.session_state:
    st.session_state.generated_graph_ok = False   

if 'quantum_button' not in st.session_state:
    st.session_state.quantum_button = False 

if 'quantum_button_Qera' not in st.session_state:
    st.session_state.quantum_button_Qera = False     

if 'screen_status' not in st.session_state:
    st.session_state.screen_status = "Initial"     


# default container that houses the image upload field
with st.container(key="ContainerFileUploader"):
    # header that is shown on the web UI
    st.subheader('Network map file upload')
    # the image upload field, the specific ui element that allows you to upload an image

    uploaded_file = st.file_uploader('Upload an Image of a Network Map', type=["png", "jpg", "jpeg"], key="FileUploaded")
    
    if uploaded_file is not None:
        # Validate the uploaded file
        is_valid, error_message, secure_file = validate_and_store_file(uploaded_file)        
        
        if not is_valid:
            st.error(f"Invalid file: {error_message}")
        else:
            # Store the secure file in session state
            st.session_state.secure_files['current_image'] = secure_file
            # Display the image
            file_data = secure_file.get_data()
            st.image(BytesIO(file_data))

            with st.container(key="ContainerGenerateGraph"):  
                # header that is shown on the web UI
                st.subheader('Generate network Graph:')      
                # this is the button that allows the user to generate a graph from uploaded image
                result_process_image = st.button("Click here to process the image and generate a network graph",key="result_process_image")
                        
                if result_process_image:
                # When process impage button being pressed  
                # 
                    if not st.session_state.bedrock_limiter.is_allowed():
                         st.error("Bedrock API rate limit reached. Please wait a moment before trying again.")
                    else:  
                        progress_text = st.success("Calculating the Network Graph, please wait")
                        
                        # First verify file integrity before processing
                        secure_file = st.session_state.secure_files.get('current_image')

                        if secure_file and secure_file.verify_integrity():
                        
                        # File integrity verified, proceed with processing
                        # Get file as BytesIO for processing
                            file_obj = get_file_as_bytesio(secure_file)

                            # Process the image
                            text,image_data = process_image_to_graph(file_obj,st.session_state.sessionId)
                            
                            if image_data is not None:
                            
                                # Store generated image securely
                                secure_graph = store_generated_image(image_data)
                                st.session_state.secure_files['generated_graph'] = secure_graph

                                st.session_state.generated_graph = image_data
                                st.session_state.generated_completion = text
                                st.session_state.screen_status = "Graph Calculated"   
                            
                            else:
                                st.warning("No image was generated, please try again")
                        else:
                        # File integrity check failed
                            st.error("File integrity check failed. Please upload the image again.")

                        # Reset the process to allow user to upload a new file
                        st.session_state.secure_files.pop('current_image', None)   

              

            # LOGIC TO DRAW DIFFERENT BUTTONS DEPENDING ON THE STATE OF THE WEB PAGE FLOW        

           
            if st.session_state.screen_status == "Graph Calculated":  
                
                st.markdown("### Network Graph")
                st.image(st.session_state.generated_graph) 
                progress_text =st.success(f"Bedrock Agent response: {st.session_state.generated_completion}")

                if st.button("Click here to continue an generate an Atom Arrangement of the graph",key="result_graph_ok"):
                    st.session_state.generated_graph_ok = True
                if st.button("Click here to request modifications on the generated graph",key="result_graph_nok"):
                    st.session_state.generated_graph_nok = True
            
           
            if st.session_state.screen_status == "Atom arrangement Calculated":

                st.markdown("### Network Graph")
                st.image(st.session_state.generated_graph) 

                st.markdown("### Atom Arrangement")
                st.image(st.session_state.generated_atom_arrangement) 
            
                if st.button("Click here to execute Quantum Algorithm on Local Quantum Simulator",key="execute_quantum"):
                    st.session_state.quantum_button = True
                if st.button("Click here to modify the atom arrangement",key="result_atom_nok"):
                    st.session_state.generated_atom_nok = True

            if st.session_state.screen_status == "Quantum Algorythim Executed":

                st.markdown("### Network Graph")
                st.image(st.session_state.generated_graph) 

                st.markdown("### Atom Arrangement")
                st.image(st.session_state.generated_atom_arrangement) 

                st.markdown("### MIS Graph calculated on local simulator")
                st.image(st.session_state.generated_mis_graph) 
            
                if st.button("Click here to execute Quantum Algorithm on Local Quantum Simulator",key="execute_quantum"):
                    st.session_state.quantum_button = True
                if st.button("Click here to execute Quantum Algorithm on Quantum QuEra processor",key="execute_quantum_procesor"):
                    st.session_state.quantum_button_Qera = True

            if st.session_state.screen_status == "Quantum Algorythim Executed on Quantum Computer":

                st.markdown("### Network Graph")
                st.image(st.session_state.generated_graph) 

                st.markdown("### Atom Arrangement")
                st.image(st.session_state.generated_atom_arrangement) 

                st.markdown("### MIS Graph")
                st.image(st.session_state.generated_mis_graph)      

                st.markdown("### MIS Graph on QuEra")               
                st.image(st.session_state.generated_mis_qera_graph )

                if st.button("Click here to execute Quantum Algorithm on Local Quantum Simulator",key="execute_quantum"):
                    st.session_state.quantum_button = True
                if st.button("Click here to execute Quantum Algorithm on Quantum QuEra processor",key="execute_quantum_procesor"):
                    st.session_state.quantum_button_Qera = True



            # LOGIC TO BE EXECUTED PER EACH BUTTON IS PRESSED       


            if st.session_state.generated_graph_ok:
                 # LOGIC TO CALCULATE THE ATOM ARRANGEMENT ONCE BUTTON IS PRESSED
                progress_text = st.success("Calculating the Atom Arrangement, please wait")

                 # Verify integrity of the graph before processing
                secure_graph = st.session_state.secure_files.get('generated_graph')
                if secure_graph and secure_graph.verify_integrity():
                 
                    if not st.session_state.bedrock_limiter.is_allowed():
                            st.error("Bedrock API rate limit reached. Please wait a moment before trying again.")
                    else:  
                            text, image_data = generate_atom_arrangement(st.session_state.sessionId)

                            # Update session state with the new image data
                            if image_data is not None:
                                # Store securely
                                secure_atom = store_generated_image(image_data)
                                st.session_state.secure_files['atom_arrangement'] = secure_atom

                                st.markdown("### Atom Arrangement")
                                st.session_state.generated_atom_arrangement = image_data
                                st.image(st.session_state.generated_atom_arrangement)
                                progress_text=st.success(f"Bedrock Agent response:{text}")
                                st.session_state.generated_graph_ok = False
                                st.session_state.screen_status = "Atom arrangement Calculated"   

                            else:
                                st.warning("No image was generated, please try again")
                                st.session_state.generated_graph_ok = False
                else:
                    st.error("Graph integrity check failed. Please regenerate the graph.")
                    st.session_state.generated_graph_ok = False

                st.button("Click to continue")    

            
                 

            if st.session_state.generated_graph_nok:
                 # LOGIC TO  MODIFY THE NETWORK GRAPH ONCE MODIFY BUTTON IS PRESSED
                 user_input = st.text_input("Write here which nodes or edges you want to change")
                 if user_input:
                    # Sanitize the input
                    sanitized_input = sanitize_text_input(user_input)
                    progress_text = st.success("Modifying the Network Graph, please wait")

                    if not st.session_state.bedrock_limiter.is_allowed():
                            st.error("Bedrock API rate limit reached. Please wait a moment before trying again.")
                    else:  
                            text, image_data = modify_network_graph(sanitized_input, st.session_state.sessionId)
                    
                            # Update session state with the new image data
                            if image_data is not None:
                                st.markdown("### Graph")
                                st.session_state.generated_graph = image_data
                                st.image(st.session_state.generated_graph)
                                progress_text=st.success(f"Bedrock Agent response:{text}")
                                st.session_state.generated_graph_nok = False
                                st.session_state.screen_status = "Graph Calculated"  
                            else:
                                st.warning("No image was generated, please try again")
                                st.session_state.generated_graph_nok = False
                    
                    st.button("Click to continue")

            if st.session_state.generated_atom_nok:
                    # LOGIC TO  MODIFY THE ATOMS ARRANGEMENT ONCE MODIFY BUTTON IS PRESSED
   
                 user_input = st.text_input("Write here which atoms arrangement you want to change")
                 if user_input:
                    sanitized_input = sanitize_text_input(user_input)
                    progress_text = st.success("Modifying the Atom Arrangement, please wait")

                    if not st.session_state.bedrock_limiter.is_allowed():
                            st.error("Bedrock API rate limit reached. Please wait a moment before trying again.")
                    else:  

                        text,image_data = modify_atom_arrangement(sanitized_input,st.session_state.sessionId)

                        # Update session state with the new image data
                        if image_data is not None:
                            st.markdown("### Atom Arrangement")
                            st.session_state.generated_atom_arrangement = image_data
                            st.image(st.session_state.generated_atom_arrangement)
                            progress_text=st.success(f"Bedrock Agent response:{text}")
                            st.session_state.generated_atom_nok = False
                            st.session_state.screen_status = "Atom arrangement Calculated"   

                        else:
                            st.warning("No image was generated, please try again")
                            st.session_state.generated_atom_nok = False
                    
                    st.button("Click to continue")        
                    
             
            if st.session_state.quantum_button:
                 
                 progress_text = st.success("Calculating the quantum algorithm on local simulator, please wait it can take some minutes")
                 
                 secure_atom = st.session_state.secure_files.get('atom_arrangement')
                 if secure_atom and secure_atom.verify_integrity():
                 
                    if not st.session_state.bedrock_limiter.is_allowed():
                            st.error("Bedrock API rate limit reached. Please wait a moment before trying again.")
                    else:  
                            text,image_data = execute_quantum_algorythm("simulator",st.session_state.sessionId)

                            if image_data is not None:
                                # Store securely
                                secure_mis = store_generated_image(image_data)
                                st.session_state.secure_files['mis_graph'] = secure_mis

                                st.markdown("### MIS Graph calculated on Local simulator")
                                st.session_state.generated_mis_graph = image_data                
                                st.image(image_data)
                                progress_text=st.success("MIS Graph calculated, please review it")
                                st.session_state.quantum_button = False
                                st.session_state.screen_status = "Quantum Algorythim Executed"
                            else:
                                st.warning("Failed to generate MIS graph")
                 else:
                        st.error("Atom arrangement integrity check failed. Please regenerate the atom arrangement.")

                 st.button("Click to continue")


            if st.session_state.quantum_button_Qera:

                 progress_placeholder = st.empty()
                 progress_placeholder.success("Sending a request for the quantum algorithm to a Quantum QuEra processor")
                 
                  # Verify integrity of atom arrangement before processing
                 secure_atom = st.session_state.secure_files.get('atom_arrangement')
                 if secure_atom and secure_atom.verify_integrity():

                    # Use the rate limiter before expensive operations

                    if not st.session_state.quantum_limiter.is_allowed():
                          st.error("Rate limit exceeded for quantum operations. Please try again later.")

                    else:
                        text,image_data = execute_quantum_algorythm("QuEra",st.session_state.sessionId)

                        task_state = quantum_task_status(text)

                        # Implement exponential backoff for status checking
                        attempt = 0
                        max_attempts = 60
                        while task_state != "COMPLETED" and attempt < max_attempts:
                            # Update the existing message in the placeholder
                            progress_placeholder.success(f"Task status is {task_state}, please wait it can take some minutes (attempt {attempt+1}/{max_attempts})")
                            
                            # Calculate wait time with exponential backoff, starting at 10 seconds and capping at 2 minutes
                            wait_time = min(10 * (1.5 ** attempt), 120)
                            time.sleep(wait_time)
                            
                            task_state = quantum_task_status(text)
                            attempt += 1
                            
                        if task_state != "COMPLETED":
                            progress_placeholder.error("Maximum attempts reached. Please check if the QuEra device is available or check task status manually in AWS Console.")
                        else:
                         # Update the message one final time when complete
                         progress_placeholder.success("Task Completed!")
                                    
                         result_aquila = quantum_task_get_result(text)
                    
                         text,image_data =  process_quantum_results(result_aquila,st.session_state.sessionId)

                         st.markdown("### MIS Graph on QuEra")
                         st.session_state.generated_mis_qera_graph = image_data                
                         st.image(image_data)
                         progress_text=st.success("MIS Graph calculated with quantum computer, please review it")
                         st.session_state.quantum_button = False
                         st.session_state.screen_status = "Quantum Algorythim Executed on Quantum Computer"
                         st.button("Click to continue")   
                        
                         st.session_state.quantum_button_Qera = False
                 else:
                     st.error("Atom arrangement integrity check failed. Please regenerate the atom arrangement.")

# Show rate limits
with st.expander(" AWS Services Usage Status"):
    # Calculate remaining calls for Bedrock
    bedrock_calls_used = len(st.session_state.bedrock_limiter.calls)
    bedrock_calls_remaining = st.session_state.bedrock_limiter.max_calls - bedrock_calls_used
    
    # Calculate remaining calls for Quantum
    quantum_calls_used = len(st.session_state.quantum_limiter.calls)
    quantum_calls_remaining = st.session_state.quantum_limiter.max_calls - quantum_calls_used
    
    # Display status
    st.write(f"Bedrock API calls remaining: {bedrock_calls_remaining}/{st.session_state.bedrock_limiter.max_calls} (resets every minute)")
    st.write(f"Bracket API calls remaining: {quantum_calls_remaining}/{st.session_state.quantum_limiter.max_calls} (resets every hour)")
    
    # Show warning if approaching limits
    if bedrock_calls_remaining < 5:
        st.warning("You're approaching the Bedrock API rate limit. Some operations may be temporarily unavailable.")
    if quantum_calls_remaining < 2:
        st.warning("You're approaching the Quantum API rate limit. Quantum operations may be temporarily unavailable.")

                  




                
           
             
