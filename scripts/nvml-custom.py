import pynvml as N
import psutil
import os.path
import subprocess
from time import sleep

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
                    processes.append(process)
                except psutil.NoSuchProcess:
                    # TODO: add some reminder for NVML broken context
                    # e.g. nvidia-smi reset  or  reboot the system
                    pass

        print(index, name, uuid)

        for proc in processes:
            p = subprocess.Popen(
                ["bash", "get-pod-from-pid.sh", str(proc['pid']) ],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE)
            out, err = p.communicate()
            container = out.split("\n")[2]
            pod = out.split("\n")[3]
            namespace = out.split("\n")[4]
            print(container,pod,namespace,proc['username'],proc['gpu_memory_usage'],proc['pid'])
        sleep(1)        

if __name__ == "__main__":
    N.nvmlInit()
    device_count = N.nvmlDeviceGetCount()
    while True:
        benchmark_gpu(device_count)
        sleep(1)
    N.nvmlShutdown()