from time import sleep

import pynvml as N
import psutil
import os.path
import subprocess
import logging
import sys

# Global LOGGER var
LOGGER = logging.getLogger(__name__)

def get_process_info(nv_process):
    """Get the process information of specific GPU process ; username, command, pid, and GPU memory usage
    Args:
        nv_process (nvmlFriendlyObject) : A process that utilize the resource of NVIDIA GPU
    Returns:
        process    (py dictionary)      : Contains the desired information of GPU process
    """

    # init dict to store process' information
    process = {}

    # Store pid and GPU memory usage into dict
    # get pid of the process    
    process['pid']              = nv_process.pid
    # Bytes to MBytes
    process['gpu_memory_usage'] = int(nv_process.usedGpuMemory / 1024 / 1024)
    
    # get process detail (process object) for given pid of a nvidia process    
    ps_process          = psutil.Process(pid = nv_process.pid)
    
    # get process username
    process['username'] = ps_process.username()

    # figure out OS command that execute the process
    # cmdline returns full path; as in `ps -o comm`, get short cmdnames.
    _cmdline = ps_process.cmdline()
    
    # sometimes, zombie or unknown (e.g. [kworker/8:2H])
    if not _cmdline:   
        process['command'] = '?'
    else:
        process['command'] = os.path.basename(_cmdline[0])
    
    return process

def benchmark_gpu():
    """Query all utilizations in each GPU and resolve them to pod information and identity"""
    
    # detect all NVIDIA GPU in machine
    device_count = N.nvmlDeviceGetCount()

    # Init empty list to store usage by each GPU
    gpus_usage   = []
    
    # Iterate through available GPU
    for index in range(device_count):
        # get the NVML object based on GPU's index target
        # get the name and uuid of NVIDIA GPU
        handle = N.nvmlDeviceGetHandleByIndex(index)
        name   = (N.nvmlDeviceGetName(handle))
        uuid   = (N.nvmlDeviceGetUUID(handle))

        # init list to store process and parent container (pod) for each process that utilizes NVIDIA
        # process        = jobs (container) that utilize NVIDA GPU
        processes       = []
        
        # Get running processes in each GPU
        try:
            nv_comp_processes = N.nvmlDeviceGetComputeRunningProcesses(handle)
        except N.NVMLError:
            nv_comp_processes = None  # Not supported

        # Get running graphics processes in each GPU                
        try:
            nv_graphics_processes = N.nvmlDeviceGetGraphicsRunningProcesses(handle)
        except N.NVMLError:
            nv_graphics_processes = None  # Not supported

        # Check if process is found or not
        if nv_comp_processes is None and nv_graphics_processes is None:
            processes = None   # Not supported (in both cases)
        else:
            nv_comp_processes     = nv_comp_processes or []
            nv_graphics_processes = nv_graphics_processes or []
            # Iterate through running process found, inspect each process 
            for nv_process in (nv_comp_processes + nv_graphics_processes):
                try:
                    process = get_process_info(nv_process)
                    processes.append(process)
                except psutil.NoSuchProcess:
                    LOGGER.info("PSutil No Such Process")
                except psutil.Error:
                    LOGGER.info("PSutil General Error")

        # Display NVIDIA GPU information
        LOGGER.info(",".join([str(index), name, uuid]))

        # iterate throught the process (container) that runs on GPU
        for proc in processes:
            # trigger bash script to resolve process pid to pod information
            p = subprocess.Popen(
                ["bash", "get-pod-from-pid.sh", str(proc['pid']) ],
                stdin  = subprocess.PIPE,
                stdout = subprocess.PIPE,
                stderr = subprocess.PIPE)
            out, err   = p.communicate()

            # Get the result from stdout, see "get-pod-from-pid" for more details
            container  = out.split("\n")[2]
            pod        = out.split("\n")[3]
            namespace  = out.split("\n")[4]

            # Display pod information and its usage
            LOGGER.info(",".join([str(index)+":",container,pod,namespace,proc['username'],str(proc['gpu_memory_usage']),str(proc['pid'])]))

        # Set one second delay between each GPU statistics    
        sleep(1)  

def setup_logging():
    """Configure custom logging format
    Returns None
    """

    # set logging level to debug    
    LOGGER.setLevel(logging.DEBUG)

    # the script is purposed to debug, so here we show all logging level into stdout
    # create a streamHandler to stdout
    ch = logging.StreamHandler(sys.stdout)

    # set logging level to debug    
    ch.setLevel(logging.DEBUG)

    # set log format
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    ch.setFormatter(formatter)

    # add handler to global logger var
    LOGGER.addHandler(ch)


# --------- Main function goes here -------- #
def main():
    # Set the custom logging format 
    setup_logging()
    LOGGER.debug("Log application is ready!")  
    
    # init the python-nvml driver
    N.nvmlInit()
    
    # Loop forever
    while True:
        # Get the stats and print them
        benchmark_gpu()

        # Set one second delay between queries
        sleep(1)

    # close the python-nvml driver        
    N.nvmlShutdown()


# --------- Main function triggered here -------- #
if __name__ == "__main__":  
    main()