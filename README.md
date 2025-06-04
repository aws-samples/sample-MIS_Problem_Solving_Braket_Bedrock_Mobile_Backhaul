# Amazon Bedrock and Amazon Braket Demo for solving a MIS Problem

This sample code demonstrates the use of Amazon Bedrock and Amazon Braket to solve a Maximum Independent Set (MIS) problem using an image as input that represents a mobile network backhaul topology where new fiber connections are going to be deployed.

## Overview of Solution


The application features a simple Streamlit frontend where users can input an image representing a set of nodes with relationships. This image is converted into a graph with nodes and edges using a Bedrock Agent. Within the same session, the Agent automatically converts the graph into an atom arrangement before invoking the Quantum Simulator. Finally, it's possible to invoke a QuEra device, and results will be displayed on the screen.


## Goal of this Solution
The goal of this repository is to provide users with the ability to use Amazon Bedrock and generative AI to automate tasks and steps required before invoking Amazon Braket. It also provides a MIS algorithm that runs properly against a local Quantum simulator using Amazon Braket libraries and against a real QPU: QuEra Aquila.

This repository includes a basic frontend to help users set up a proof of concept in just a few minutes.

When a user interacts with the Solution, the flow is as follows:

The user uploads an image file to the Streamlit app. This image must contain a structure that can be converted to a graph (app.py).

Once the graph is extracted from the image, the user is asked to either continue generating an Atom Arrangement of the graph or modify the inferred graph if any mistakes were made by the Bedrock Agent (app.py).

After the Atom Arrangement is generated, the user is asked to either continue executing the algorithm on the local quantum simulator or modify the atom arrangement if there are any errors (app.py).

Once the algorithm is executed in the simulator, the results are shown, and the end user is asked to execute the algorithm on a QPU (app.py).



# How to use this Repo:
This code must be used as companion of the blog ********

## Prerequisites:

1. [AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html) installed and configured with access to Amazon Bedrock.
2. Amazon Braket Terms & Conditions: in permission and settings you have accepted terms and enabled the use of braket
3. Amazon Braket Service-linked role: in permission and settings you have created a service-link role
4. Get access in Amazon Bedrock to Claude 3.5 in us-west2
5. [Python](https://www.python.org/downloads/) v3.11 or greater. The Solution runs on python. 



## Steps
1. Clone the repository to your local machine.

    ```
    git clone https://github.com/aws-samples/sample-MIS_Problem_Solving_Braket_Bedrock_Mobile_Backhaul/
    ```
    
    The file structure of this solution is broken into these files
    
    * `requirements.txt` - all the requirements needed to get the sample application up and running.
    * `app.py` - The streamlit frontend
    * `bedrock_backend_functions.py` - The functions to invoke bedrock agent
    * `env.local` - environment file
    * `Prompts.py` - File that contain all the prompts being used
    * `Quantum_API.py` - python functions to be executed for interacting with Amazon Braket
    * `create_bedrock_agent.py` - python function to be executed the first time and create a bedrock agent with code interpreter and the required iam roles
    * `cleanup_resources.py` - python function to be executed for cleaning the agent and roles being created
    * `secure_file_handler.py` - python function that manage internal files on a secured way

    

1. Open the repository in your favorite code editor. In the terminal, navigate to the POC's folder:
    ```zsh
    cd bedrock_braket_mis
    ```

3. Log in your AWS Account

3. Configure the python virtual environment, activate it & install project dependencies. *Note: each POC has it's own dependencies & dependency management.*
    ```zsh
    python3 -m venv .env
    source .env/bin/activate
    pip install -r requirements.txt
    ```

4. Update ".env.local" file with your profile name and login in AWS assuming this profile. Update also foundation

     ```zsh
    profile_name=<AWS_CLI_PROFILE_NAME>
    
    ```

5. Execute `setup.py` program to create the agent and access permisions to Bedrock and Braket
    
    ```zsh
    python3 create_bedrock_agent.py
    ```

6. Update ".env.local" file with the agentid, agentAliasId and role_name values printed in screen 
    
    ```zsh
    agentId=<AGENT_ID>
    agentAliasId=<AGENT_ALIAS>
    role_name=<ROLE_NAME>
    ```  

7. Start the POC from your terminal
    ```zsh
    streamlit run app.py
    ```
This should start the POC and open a browser window to the application. 




## Security

See [CONTRIBUTING](CONTRIBUTING.md#security-issue-notifications) for more information.

## License

This library is licensed under the MIT-0 License. See the LICENSE file.

