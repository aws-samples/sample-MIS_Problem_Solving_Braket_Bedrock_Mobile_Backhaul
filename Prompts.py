# PROMPT LIBRARY


PROMPT_LLM_DIRECT_INVOCATION_IMAGE_PROCESSING = """
    
        You are a map analyser that is going to generate phyton code analysing attached image that contains a map with red circles and red lines connecting pair of red circles. 

        Your goal is to analyse the image and identify all red circles with a number and categorise them as nodes. 
        Your goal is to analyse the image and identify all red lines that connects red circles and categorise them as edges. 
        For achieving the goal you first will identify the red circles and then analyse per each circle which are the connections with other circles.

        Here are some important rules for the analysis of the image:
        - When analysing the image consider that red lines can be horizontal, vertical or diagonal.
        - A red line is always a straight line, discard other types of lines that are not red neither straight .
        - A red line always connect a pair of red circles with a number.
        - Connect means that red line starts in or near a red circle and finish near or in another red circle.
        - There is not any red circle without any red line.
        - Do not HALLUCINATE and create edges when there are not red lines in the image that connect two red circles.
        - Do not consider red circle proximity to create a line between two red circles. Only create an edge when there is a red line connecting two red circles.
        - Do not consider other lines that are not red lines and correspond to other objects in the map like streets.
        - Do not consider a line that connects two circles but there is another one in the middle. In that case there are two lines and only connect the first circle with the one in the middle and the one in the middle with the other circle. 

        Here are some important rules for the response:
        - Provide only the python code do not add any text or comment in the code.
        - Create a layout and locate the nodes in the same place found in the map and draw it.
        - Consider that the response is going to be executed automatically as code so avoid any error due to errors in the code or comments. 

    """

PROMPT_ANALYSE_UPLOADED_IMAGE = """You are a map analyser that is going to generate a graph using phyton code analysing attached image that contains a map with red circles and red lines connecting pair of red circles. 

        Your goal is to analyse the image and identify all red circles with a number and categorise them as nodes. 
        Your goal is to analyse the image and identify all red lines that connects red circles and categorise them as edges. 
        For achieving the goal you first will identify the red circles and then analyse per each circle which are the connections with other circles.

        Here are some important rules for the analysis of the image:
        - When analysing the image consider that red lines can be horizontal, vertical or diagonal.
        - A red line is always a straight line, discard other types of lines that are not red neither straight .
        - A red line always connect a pair of red circles with a number.
        - Connect means that red line starts in or near a red circle and finish near or in another red circle.
        - There is not any red circle without any red line.
        - Do not HALLUCINATE and create edges when there are not red lines in the image that connect two red circles.
        - Do not consider red circle proximity to create a line between two red circles. Only create an edge when there is a red line connecting two red circles.
        - Do not consider other lines that are not red lines and correspond to other objects in the map like streets.
        - Do not consider a line that connects two circles but there is another one in the middle. In that case there are two lines and only connect the first circle with the one in the middle and the one in the middle with the other circle. 

        Here are some important rules for the response:
        - Provide a graph generated using python code.
        - Create a layout and locate the nodes in the same place found in the map and draw it.
        - Consider that the response is going to be executed automatically as code so avoid any error due to errors in the code or comments. 

        """

PROMPT_GENERATE_GRAPH = "Execute the following code and generate only one image based in the code: "

PROMPT_GENERATE_ATOM_ARRANGEMENT = """Convert previous Graph and image generated into a unit disk graph for an atom arrangement in braket.
                                             Start with first node at position (0,0) and then place it connected nodes at a distance of 1 
                                             always using only horizontal or vertical lines, never diagonals.
                                             Please when placing the nodes consider that non connected nodes cannot be at a distance of 1. 
                                             So once placed some nodes based in their connections be aware that new placed nodes can be connected
                                             at a distance of 1 of previous places nodes by mistake. 
                                             Avoid this to happen by one placed all nodes review again and check if any node with no connection is placed
                                             at a distance of 1 and modify the placement of the node mainly by placing in verticaly instead of horizontaly and viceversa.
                                             
                                             Here is an example:
                                           
                                             Graph has 5 nodes. 
                                             Node 0 is connected to 1,2,3 so distance on those nodes has to be the vertex distance 
                                             and atoms are next to each other
                                             Node 3 is connected to node 4 so distance between node 3 and node 4 has to be the vertex distance
                                             and atoms are next to each other but node 4 is not next to any other one node meaning is not a vertex distance
                                             to another atom 

                                             Code sample for this Graph
                                             import numpy as np
                                             import matplotlib.pyplot as plt  # required for plotting
                                                
                                             from braket.ahs.atom_arrangement import AtomArrangement
                                                
                                                a = 1 # grid vertex distance Use same value of the QuEra Training.
                                                row_max = 4
                                                col_max = 4

                                                atoms = AtomArrangement()
                                                atoms.add(np.array([0,0]) * a) # 0
                                                atoms.add(np.array([1,0]) * a) # 1
                                                atoms.add(np.array([-1,0]) * a) # 2
                                                atoms.add(np.array([0,1]) * a) # 3
                                                atoms.add(np.array([0,2]) * a) # 4
                                           
                                                plt.figure(figsize=(7,7))
                                                xs, ys = [atoms.coordinate_list(dim) for dim in (0, 1)]
                                                plt.plot(xs, ys, 'r.', ms=15)
                                                for idx, (x, y) in enumerate(zip(xs, ys)):
                                                    plt.text(x, y, f" {idx}", fontsize=12)
                                                plt.xticks(np.arange(-5*a, 5*a, step=a))
                                                plt.yticks(np.arange(-5*a, 5*a, step=a))
                                                plt.grid(color='gray', alpha=0.5, lw=1, ls=':')
                                                plt.show()  # this is the return graph you need to show
                                            
                                           
                                             Here is another example:
                                           
                                             Graph has 5 nodes. 
                                             Node 0 is connected to 1,2 so distance on those nodes has to be the vertex distance 
                                             and atoms are next to each other
                                             Node 3 is connected to node 2 so distance between node 2 and node 2 has to be the vertex distance
                                             and atoms are next to each other but node 3 is not next to any other one node meaning is not a vertex distance
                                             to another atom 
                                             Node 4 is connected to node 1 so distance between node 4 and node 1 has to be the vertex distance
                                             and atoms are next to each other but node 4 is not next to any other one node meaning is not a vertex distance
                                             to another atom 
                                    
                                             Code sample for this Graph
                                             import numpy as np
                                             import matplotlib.pyplot as plt  # required for plotting
                                                
                                             from braket.ahs.atom_arrangement import AtomArrangement
                                                
                                                a = 1 # grid vertex distance Use same value of the QuEra Training.
                                                row_max = 4
                                                col_max = 4

                                                atoms = AtomArrangement()
                                                atoms.add(np.array([0,0]) * a) # 0
                                                atoms.add(np.array([1,0]) * a) # 1
                                                atoms.add(np.array([-1,0]) * a) # 2
                                                atoms.add(np.array([-2,0]) * a) # 3
                                                atoms.add(np.array([2,0]) * a) # 4
                                           
                                                plt.figure(figsize=(7,7))
                                                xs, ys = [atoms.coordinate_list(dim) for dim in (0, 1)]
                                                plt.plot(xs, ys, 'r.', ms=15)
                                                for idx, (x, y) in enumerate(zip(xs, ys)):
                                                    plt.text(x, y, f" {idx}", fontsize=12)
                                                plt.xticks(np.arange(-5*a, 5*a, step=a))
                                                plt.yticks(np.arange(-5*a, 5*a, step=a))
                                                plt.grid(color='gray', alpha=0.5, lw=1, ls=':')
                                                plt.show()  # this is the return graph you need to show
                                                 
                                               
                                            """



PROMPT_MODIFY_NETWORK_GRAPH = "Change previous graph modifiying nodes or connections using the following instructions: "
PROMPT_MODIFY_ATOM_ARRANGEMENT_GRAPH = "Change previous atom arrangement modifiying it using the following instructions: "

PROMPT_CREATE_INPUT_QUANTUM_EXEC_FUNCTION = """With previous generated atom arrangement 
                                            return only the input for the following function 
                                            
                                            def QuantumSimulatorExecute(nodes):

                                                a = 7e-6  # grid vertex distance Use same value of the QuEra Training
                                                row_max = 4
                                                col_max = 4
                                                
                                                atoms = AtomArrangement()
                                                
                                                # Add atoms directly using the coordinates from nodes input
                                                for node in nodes:
                                                    coord = np.array(node, dtype=float)
                                                    atoms.add(coord * a)
                                            
                                            Here is an example of a function invokation, do the same but with the previous calculated atom arrangement

                                            # Define the nodes (coordinates of atoms)
                                                    nodes = [[0,0],[1,0],[-1,0],[0,1],[1,1]]

                                                    # Call the function
                                                    atom_arrangement = QuantumSimulatorExecute(nodes)
                                            
                                            Return only the input as is going to be used in this way to invoke the function; for the given example you just return [[0,0],[1,0],[-1,0],[0,1],[1,1]] 
                                            don't you add the comments that identify each node
                                            just the double values of the coordinates. Also don't you add any line break  or other character that is going to give an error once tried to get converted to double. Dont you
                                            add None node at the end or something like this, follow strictly yhe format being given in the sample
                                           """

