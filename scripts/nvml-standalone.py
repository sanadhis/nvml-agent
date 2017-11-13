import pynvml as N
import psutil
import os.path
import subprocess
import socket
from time import sleep

class GPUStat:
    def __init__(self):
        pass    

    @staticmethod
    def new_query():
        """Query the information of all the GPUs on the machine & Trace Pod Processes that utilize them"""
        
        N.nvmlInit()
        hostname = socket.gethostname()        

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
            
            device_count = N.nvmlDeviceGetCount()    
            gpu_usages   = []
            
            for index in range(device_count):
                handle = N.nvmlDeviceGetHandleByIndex(index)
                name   = (N.nvmlDeviceGetName(handle))
                uuid   = (N.nvmlDeviceGetUUID(handle))

                processes       = []
                parentProcesses = []
                
                try:
                    temperature = N.nvmlDeviceGetTemperature(handle, N.NVML_TEMPERATURE_GPU)
                except:
                    temperature = None

                try:
                    memory = N.nvmlDeviceGetMemoryInfo(handle) # in Bytes
                except N.NVMLError:
                    memory = None  # Not supported

                try:
                    utilization = N.nvmlDeviceGetUtilizationRates(handle)
                except N.NVMLError:
                    utilization = None  # Not supported

                try:
                    power = N.nvmlDeviceGetPowerUsage(handle)
                except:
                    power = None

                try:
                    power_limit = N.nvmlDeviceGetEnforcedPowerLimit(handle)
                except:
                    power_limit = None

                try:
                    nv_comp_processes = N.nvmlDeviceGetComputeRunningProcesses(handle)
                except N.NVMLError:
                    nv_comp_processes = None  # Not supported
                try:
                    nv_graphics_processes = N.nvmlDeviceGetGraphicsRunningProcesses(handle)
                except N.NVMLError:
                    nv_graphics_processes = None  # Not supported

                if nv_comp_processes is None and nv_graphics_processes is None:
                    processes = None   # Not supported (in both cases)
                else:
                    nv_comp_processes     = nv_comp_processes or []
                    nv_graphics_processes = nv_graphics_processes or []

                    for nv_process in (nv_comp_processes + nv_graphics_processes):
                        # TODO: could be more information such as system memory usage,
                        # CPU percentage, create time etc.
                        try:
                            process       = get_process_info(nv_process)
                            parentProcess = get_parent_process_info(nv_process)

                            processes.append(process)
                            parentProcesses.append(parentProcess)
                        except psutil.NoSuchProcess:
                            print("Error No Such Process")
                        except psutil.Error:
                            print("Error: PSutil General")

                pod_details = []
                for proc,parentProc in zip(processes,parentProcesses):
                    pod        = get_pod_info(parentProc.pid)
                    pod_detail = {
                                    "pod_container_name": pod['container_name'],
                                    "pod_name"          : pod['name'],
                                    "pod_namespace"     : pod['namespace'],
                                    "pod_proc_username" : proc['username'],
                                    "pod_gpu_usage"     : proc['gpu_memory_usage'],
                                    "pod_proc_pid"      : proc['pid']
                                }
                    pod_details.append(pod_detail)

                per_gpu_usage = {
                                "hostname" : hostname,
                                "gpu_name" : name,
                                "gpu_index": index,
                                "gpu_uuid" : uuid,
                                "gpu_usage": pod_details
                            }

                gpu_usages.append(per_gpu_usage)
            
            return gpu_usages
        
        pods_gpu_usage = benchmark_gpu()
        N.nvmlShutdown()
        return pods_gpu_usage        

if __name__ == "__main__":
    gpu_stats       = GPUStat()
    pods_gpu_usage  = gpu_stats.new_query()
    print(pods_gpu_usage)