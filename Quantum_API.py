# Required libraries import

from braket.ahs.atom_arrangement import AtomArrangement
from braket.aws import AwsDevice
from braket.devices import Devices
from braket.timings.time_series import TimeSeries
from braket.ahs.driving_field import DrivingField
from braket.ahs.analog_hamiltonian_simulation import AnalogHamiltonianSimulation
from braket.devices import LocalSimulator
from braket.aws import AwsQuantumTask
from braket.aws import AwsSession
import boto3
from dotenv import load_dotenv
import ast  # For safe evaluation of literals


from collections import Counter
import networkx as nx
import numpy as np
import os

load_dotenv(dotenv_path='env.local')
profile_name = os.getenv("profile_name")
session = boto3.Session(profile_name=profile_name)
aws_session = AwsSession(boto_session=session)
device_qpu = AwsDevice(Devices.QuEra.Aquila, aws_session=aws_session)
# quantumComputer = os.getenv('quantumComputer')


def quantum_simulator_execute(nodes,mode):

    a = 7e-6  # grid vertex distance Use same value of the QuEra Training
    row_max = 4
    col_max = 4
    
    atoms = AtomArrangement()
    
    # Add atoms directly using the coordinates from nodes input
    
    # Extract the string representation from the tuple
    #nodes_str = nodes[0]
    #print(f"Nodes string: {nodes_str}")
    # Convert string to list using eval
    try:
        # Use ast.literal_eval instead of eval for safe parsing of literal structures
        nodes_list = ast.literal_eval(nodes)
        
        # Add atoms for each coordinate pair
        for node in nodes_list:
            coord = np.array(node, dtype=float)
            atoms.add(coord * a)
            
    except Exception as e:
        print(f"Error processing nodes: {e}")
        return None
   
    # Extract QPU values to be used in the program, directly from Braket API
    # We use maximum omega and minimum time ramp value allowed by the QPU in May 2025.
    # In case the QPU evolves and those values changes affecting the algorthim, we'll overwrite those value.
    capabilities = device_qpu.properties.paradigm
    cap_ryd = capabilities.dict()['rydberg']
    omega_max_QPU = float(cap_ryd['rydbergGlobal']['rabiFrequencyRange'][1]) # rad/s
    time_ramp = float(cap_ryd['rydbergGlobal']['timeDeltaMin'])
    omega_max_QPU = 15800000
    time_ramp = 5e-08
    time_ramp_options = [0.8e-6, time_ramp] 
    omega_max_options = [2*np.pi*2.5*1e6, omega_max_QPU]
    delta_max_options = [2*np.pi*6.85*1e6, omega_max_QPU*2.7]
    
    # Driving Fields creatiion.

    time_max = 4e-6  # seconds 
    time_ramp = time_ramp_options[1]
    omega_max = omega_max_options[1] 
    delta_end= delta_max_options[1] 
    delta_start = -delta_end 

    omega = TimeSeries()
    omega.put(0.0, 0.0)
    omega.put(time_ramp, omega_max)
    omega.put(time_max - time_ramp, omega_max)
    omega.put(time_max, 0.0)
    
    delta = TimeSeries()
    delta.put(0.0, delta_start)
    delta.put(time_ramp, delta_start)
    delta.put(time_max - time_ramp, delta_end)
    delta.put(time_max, delta_end)
    
    phi = TimeSeries().put(0.0, 0.0).put(time_max, 0.0)
    
    drive = DrivingField(
        amplitude=omega,
        phase=phi,
        detuning=delta
    )

    # Atom Arrangement and Driving Field creates the QPU Program
   
    ahs_program = AnalogHamiltonianSimulation(
    register=atoms,
    hamiltonian=drive
    )

    # Simulate QPU with the Program in the local simulator.
    if mode == 'simulator':
     device = LocalSimulator("braket_ahs")
     result_simulator = device.run(
        ahs_program,
        shots=1000
     ).result()  # takes about 150 seconds


     # Collect simulation results and show the most frequent atom configuration.

     show_n_result = 1

     states = ["e", "r", "g"]
     state_labels = []
     for shot in result_simulator.measurements:
        pre = shot.pre_sequence
        post = shot.post_sequence
        state_idx = np.array(pre) * (1 + np.array(post))
        state_labels.append("".join([states[s_idx] for s_idx in state_idx]))

     occurence_count = Counter(state_labels)

     most_frequent_regs = occurence_count.most_common(show_n_result)
     return  most_frequent_regs
    
    if mode == 'Qera':
     
     # Select the QPU device
     # aquila_qpu = AwsDevice(quantumComputer)
     # print(profile_name)
     # print(device_qpu)
     aquila_qpu = device_qpu
     # aquila_qpu = AwsDevice("arn:aws:braket:us-east-1::device/qpu/quera/Aquila",aws_session=aws_session)

     # use the same program simulated in the local simulator, but adapt the 
     # values to discrete values as required by the QPU
     discretized_ahs_program = ahs_program.discretize(aquila_qpu)

     # Launch the Task, retrieve and show ARN of the task and its status.
     task = aquila_qpu.run(discretized_ahs_program, shots=1000)
   
     metadata = task.metadata()
     task_arn = metadata['quantumTaskArn']
     task_status = metadata['status']
   
     print(f"ARN: {task_arn}")
     print(f"status: {task_status}")

     return task_arn,task_status


def quantum_task_status(task_arn):

    task = AwsQuantumTask(task_arn,aws_session=aws_session)

    metadata = task.metadata()
    task_arn = metadata['quantumTaskArn']
    task_status = metadata['status']
   

    return task_status




def quantum_task_get_result(task_arn):

    task = AwsQuantumTask(task_arn,aws_session=aws_session)
    result_aquila = task.result()

    # Collect simulation results and show the most frequent atom configuration.

    show_n_result = 1

    states = ["e", "r", "g"]
    state_labels = []
    for shot in result_aquila.measurements:
        pre = shot.pre_sequence
        post = shot.post_sequence
        state_idx = np.array(pre) * (1 + np.array(post))
        state_labels.append("".join([states[s_idx] for s_idx in state_idx]))

    occurence_count = Counter(state_labels)

    most_frequent_regs = occurence_count.most_common(show_n_result)
    return  most_frequent_regs
