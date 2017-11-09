import pynvml as N
import psutil
import os.path
import subprocess
import socket
from time import sleep

HOSTNAME = socket.gethostname()

def get_process_info(nv_process, pid):
    """Get the process information of specific pid"""
    process = {}
    ps_process = psutil.Process(pid=pid)
    process['username'] = ps_process.username()
    # cmdline returns full path; as in `ps -o comm`, get short cmdnames.
    _cmdline = ps_process.cmdline()
    if not _cmdline:   # sometimes, zombie or unknown (e.g. [kworker/8:2H])
        process['command'] = '?'
    else:
        process['command'] = os.path.basename(_cmdline[0])
    # Bytes to MBytes
    process['gpu_memory_usage'] = int(nv_process.usedGpuMemory / 1024 / 1024)
    process['pid'] = nv_process.pid
    return process

def get_parent_process_info(process_pid):
    process  = psutil.Process(pid=process_pid)
    while process.parent().name() != "docker-containerd-shim":
        process = process.parent()

    return process

def get_pod_info(pod_pid):
    p = subprocess.Popen(
                    ["docker", "ps", "-q"],
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE)
    out,err = p.communicate()
    container_ids = out.split("\n")
    pod = {}
    for container_id in container_ids:
        p = subprocess.Popen(
                        ["docker", "inspect", "--format","'{{.State.Pid}} {{.Name}} {{.Id}}'",container_id],
                        stdin=subprocess.PIPE,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE)
        out, err = p.communicate()
        pod_info = out.split("\n")[0].replace("'","").split()
        if pod_info[0] == str(pod_pid):
            break
    
    pod['pid']            = pod_info[0]
    pod_container_details = pod_info[1].split("_")

    pod['container']      = pod_container_details[1]        
    pod['name']           = pod_container_details[2]
    pod['namespace']      = pod_container_details[3]

    pod['container_id']   = pod_info[2]   

    return pod

def benchmark_gpu(device_count):
    for index in range(device_count):
        handle = N.nvmlDeviceGetHandleByIndex(index)
        name = (N.nvmlDeviceGetName(handle))
        uuid = (N.nvmlDeviceGetUUID(handle))
        
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

        processes = []
        parentProcesses = []
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
            nv_comp_processes = nv_comp_processes or []
            nv_graphics_processes = nv_graphics_processes or []
            for nv_process in (nv_comp_processes + nv_graphics_processes):
                # TODO: could be more information such as system memory usage,
                # CPU percentage, create time etc.
                try:
                    process = get_process_info(nv_process, nv_process.pid)
                    parentProcess = get_parent_process_info(nv_process.pid)

                    processes.append(process)
                    parentProcesses.append(parentProcess)

                except psutil.NoSuchProcess:
                    # TODO: add some reminder for NVML broken context
                    # e.g. nvidia-smi reset  or  reboot the system
                    pass

        print(HOSTNAME, name, index,  uuid)

        for proc,parentProc in zip(processes,parentProcesses):
            pod = get_pod_info(parentProc.pid)
            print(pod['container'],pod['name'],pod['namespace'],proc['username'],proc['gpu_memory_usage'],proc['pid'])
        sleep(1)        

if __name__ == "__main__":
    N.nvmlInit()
    device_count = N.nvmlDeviceGetCount()
    while True:
        benchmark_gpu(device_count)
        sleep(1)
    N.nvmlShutdown()