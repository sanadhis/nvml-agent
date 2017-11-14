from time import sleep
from datetime import datetime
from influxdb import InfluxDBClient
from influxdb.exceptions import InfluxDBClientError

import os.path
import pynvml as N
import psutil
import subprocess
import socket
import sys
import yaml

# --------- Class GPUStat : query, functions and process needed to obtain the culprit (pods) that execute jobs in GPU -------- #
class GPUStat(object):
    def __init__(self, gpus_pod_usage={}):
        """Constructor of GPUStat class
        Args:
            gpus_pod_usage (py dictionary, default empty): Information of GPU usage by Pods (should be dict)
        Fields: 
            gpus_pod_usage (py dictionary) : A detailed information of per-container GPU utilization in each GPU on a machine
            hostname       (string)        : The hostname of current machine
            query_time     (datetime)      : Time information when the object created
        """
        self.gpus_pod_usage = gpus_pod_usage

        # attach host and time information of each GPUStat
        self.hostname       = socket.gethostname()
        self.query_time     = datetime.now()

    @staticmethod
    def new_query():
        """Query the information of all the GPUs on the machine & Trace Pod Processes that utilize them
        Returns:
        GPUStat Object : Statistics and details to account GPU usage by Pods
        """
        
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

        def get_parent_process_info(nv_process):
            """Get the information of parent container (pod) of specific container pid    
            Args:
                nv_process (nvmlFriendlyObject) : A process that utilize the resource of NVIDIA GPU
            Returns:
                process    (psutil.Process)     : Prosess object for parent container (pod)
            """

            # get process detail (process object) for given pid of a nvidia process    
            process  = psutil.Process(pid = nv_process.pid)

            # In context of kubernetes, pod is parent process of containers (jobs) that run across the nodes in kubernetes cluster
            # Loop until we find the parent container (pod), the keyword is "docker-containerd-shim" (daemonless containers)
            while process.parent().name() != "docker-containerd-shim":
                process = process.parent()

            return process

        def get_pod_info(pod_pid):
            """Get the pod information ; pod pid, container's name, pod name, pod namespace, container's id
            Args:
                pod_pid (int)           : Pid of given pod
            Returns:
                pod     (py dictionary) : Contains the desired information of pod.
            """

            # init dict to store pod's information
            pod = {}

            # Equal to "docker ps -q" in shell terminal, listing all ids of running containers
            docker_ps                      = subprocess.Popen(
                                                ["docker", "ps", "-q"],
                                                stdin=subprocess.PIPE,
                                                stdout=subprocess.PIPE,
                                                stderr=subprocess.PIPE
                                                )
            docker_ps_out, docker_ps_err   = docker_ps.communicate()

            # Store the result of "docker ps -q" as an array of containers' id
            container_ids = docker_ps_out.split("\n")

            # Loop through all container ids, 
            # inspect each and try to find container details that match given pod_pid
            for container_id in container_ids:
                # Equal to "docker inspect --format '{{.State.Pid}} {{.Name}} {{.Id}}' [container_id]" in shell,
                # Inspect pid, docker process's name, and container's id of each container's id 
                # (some are redundants, but it is to ensure we inspect the same process)
                docker_inspect                         = subprocess.Popen(
                                                        ["docker", "inspect", "--format","'{{.State.Pid}} {{.Name}} {{.Id}}'",container_id],
                                                        stdin=subprocess.PIPE,
                                                        stdout=subprocess.PIPE,
                                                        stderr=subprocess.PIPE)
                docker_inspect_out, docker_inspect_err = docker_inspect.communicate()

                # The result of docker inspect should contain desired information
                # Split the result of docker inspect: [process_pid/pod_pid] [docker_process_name] [container_id]
                pod_info = docker_inspect_out.split("\n")[0].replace("'","").split()

                # Break the loop if we find the desired container details of a pod
                if pod_info[0] == str(pod_pid):
                    break
            
            # The name format for each running docker process in kubernetes is as follows:
            # /k8s_[pod-name]_[container_name]_[pod_namespace]_[random_hash]
            # Split them as pod_containers_details to obtain "container_name", "name", "namespace"
            pod_container_details = pod_info[1].split("_")
            
            # Store the results
            pod['pid']            = pod_info[0]
            pod['container_name'] = pod_container_details[1]        
            pod['name']           = pod_container_details[2]
            pod['namespace']      = pod_container_details[3]
            pod['container_id']   = pod_info[2]   

            return pod

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
                # parent process = parent container (pod) that utilize NVIDIA GPU
                processes       = []
                parentProcesses = []
                
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
                    # and find corresponding pod (parent container) that run the process
                    for nv_process in (nv_comp_processes + nv_graphics_processes):
                        try:
                            process       = get_process_info(nv_process)
                            parentProcess = get_parent_process_info(nv_process)

                            processes.append(process)
                            parentProcesses.append(parentProcess)
                        except psutil.NoSuchProcess:
                            print("Error No Such Process")
                        except psutil.Error:
                            print("Error: PSutil General")

                # list, each GPU can have >1 running process(es) (but in Kubernetes 1.8, they should come from same container/pod)
                pod_details = []

                # iterate throught the pair process (container) & parent process (pod/parent container)
                for proc,parentProc in zip(processes,parentProcesses):
                    # get pod detail from parentProc.pid
                    pod        = get_pod_info(parentProc.pid)
                    # store the detail
                    pod_detail = {
                                    "pod_container_name": pod['container_name'],
                                    "pod_name"          : pod['name'],
                                    "pod_namespace"     : pod['namespace'],
                                    "pod_proc_username" : proc['username'],
                                    "pod_gpu_usage"     : proc['gpu_memory_usage'],
                                    "pod_proc_pid"      : proc['pid']
                                }
                    # information of each pod that runs jobs in kubernetes cluster
                    pod_details.append(pod_detail)

                # Store utilization per gpu
                per_gpu_usage = {
                                "gpu_name" : name,
                                "gpu_index": index,
                                "gpu_uuid" : uuid,
                                "gpu_usage": pod_details
                               }

                # append per-gpu usage
                gpus_usage.append(per_gpu_usage)
            
            return gpus_usage
        
        # init the python-nvml driver
        N.nvmlInit()

        # get current utilization in each GPU and corresponding pods details
        gpus_pod_usage = benchmark_gpu()

        # close the python-nvml driver        
        N.nvmlShutdown()

        # return query result as GPUStat object
        return GPUStat(gpus_pod_usage)        

# --------- Class InfluxdbDriver : handle write process of GPU stats into Influxdb server -------- #
class InfluxDBDriver:
    def __init__(self, influxdb_host, influxdb_port, influxdb_user, influxdb_pass, influxdb_db, *args):
    """Constructor of InfluxDBDriver class
    Args:
        influxdb_host (string) : Hostname (URL) of influxdb server, to store the data for.
        influxdb_port (string) : Port which infludb server is running on.
        influxdb_user (string) : Access username.
        influxdb_pass (string) : Access password.
        influxdb_db   (string) : db name to write the GPU stats for.
    Fields: 
        client (InfluxDBClient): Connection object for the given Influxdb
    """

        # Try connecting to influxdb instance
        try:
            client = InfluxDBClient(influxdb_host,
                                    influxdb_port,
                                    influxdb_user,
                                    influxdb_pass,
                                    influxdb_db
                                   )
        except InfluxDBClientError:
            client = None
            print("Not Working") 

        # this->object->client
        self.client = client

    def write(self, gpu_stats):
    """Write the gpus' usage statistics to influxdb server
    Args:
        gpu_stats (GPUStat Obj) : Statistics and details to account GPU usage by Pods.
    Returns: 
        None
    """
        # get hostname and timestamp of the query
        nodename  = gpu_stats.hostname
        stat_time = gpu_stats.query_time

        # iterate though all available GPU in machine
        for gpu_stat in gpu_stats.gpus_pod_usage:
            # Assign and gather identity of each GPU
            gpu_name  = gpu_stat["gpu_name"]
            gpu_index = gpu_stat["gpu_index"]
            gpu_uuid  = gpu_stat["gpu_uuid"]
            gpu_usage = gpu_stat["gpu_usage"]
            
            # iterate through all pods' processes in each gpu     
            for usage in gpu_usage:
                # Assign and gather information of pods' utilization
                pod_container_name = usage['pod_container_name']
                pod_name           = usage['pod_name']
                namespace_name     = usage['pod_namespace']
                pod_gpu_usage      = usage['pod_gpu_usage']

                # Form the data to write with json format
                json_body = [
                                {
                                    "measurement": "gpu/usage",
                                    "tags": {
                                        "nodename" : nodename,
                                        "gpu_name" : gpu_name,
                                        "gpu_uuid" : gpu_uuid,
                                        "gpu_index": gpu_index,
                                        "pod_name" : pod_name,
                                        "pod_container_name" : pod_container_name,
                                        "namespace_name" : namespace_name
                                    },
                                    "time": stat_time,
                                    "fields": {
                                        "value": pod_gpu_usage
                                    }
                                }
                            ]

                # attempt writing into influxdb
                try:
                    self.client.write_points(json_body)
                except InfluxDBClientError as err:
                    print("Influx is not working here: ",err)             
                    pass 

# --------- Main function goes here -------- #
def main():
    """Read stats from GPU and write them into Influxdb server"""

    try:
        # Read configuration file with YAML format
        conf_file = sys.argv[1]
        with open(conf_file, "r") as  ymlfile:
            influx_cfg  = (yaml.load(ymlfile))

        # Request the GPU statistics
        gpu_stats = GPUStat().new_query()
        print(gpu_stats.gpus_pod_usage)
        
        # Connect into Influxdb instance using given configuration
        influxClient = InfluxDBDriver(**influx_cfg)
        # Write the statistics into Influxdb        
        influxClient.write(gpu_stats)
    
    except IndexError:
        print("Error: Configuration file is not given!")
    except IOError:
        print("Error: File does not exist!")
    except:
        print("Error")


# --------- Main function triggered here -------- #
if __name__ == "__main__":
    main()