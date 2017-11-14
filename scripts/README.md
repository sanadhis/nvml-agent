# NVML Agent: Install collectors for NVIDIA-GPU across Kubernetes Cluster

## Testing the nvml-agent with InfluxDB Driver

1. Make sure you have **python-influxdb** and **pynvml** in your machine:

2. Create conf.yaml configuration file (**note that conf.yaml in scripts/ is ignored**):
  ```bash
  $ touch conf.yaml
  ```
  example:
  ```bash
  influxdb_host: "localhost"
  influxdb_port: "8086"
  influxdb_user: "root"
  influxdb_pass: "root"
  influxdb_db: "k8s"
  ```

3. Execute nvml-agent.py with /path/to/conf/file as argument:
  ```bash
  $ python nvml-agent.py "conf.yaml"
  ```

## Testing the nvml.py only
**Note that this script will run forever and useful for debugging process**

1. Make sure you have **pynvml** in your machine:

2. Execute nvml.py:
  ```bash
  $ python nvml-agent
  ```

## Testing the pid-to-pod resolutions with get-pod-from-pid.sh

1. Make sure you have nvidia driver working in your machine. Test it by issuing:
  ```
  $ nvidia-smi
  Tue Nov 14 10:52:28 2017
+-----------------------------------------------------------------------------+
| NVIDIA-SMI 384.90                 Driver Version: 384.90                    |
|-------------------------------+----------------------+----------------------+
| GPU  Name        Persistence-M| Bus-Id        Disp.A | Volatile Uncorr. ECC |
| Fan  Temp  Perf  Pwr:Usage/Cap|         Memory-Usage | GPU-Util  Compute M. |
|===============================+======================+======================|
|   0  GeForce GTX TIT...  Off  | 00000000:04:00.0 Off |                  N/A |
| 22%   31C    P8    15W / 250W |     11MiB / 12207MiB |      0%      Default |
+-------------------------------+----------------------+----------------------+
|   1  GeForce GTX TIT...  Off  | 00000000:83:00.0 Off |                  N/A |
| 22%   27C    P8    14W / 250W |  11639MiB / 12207MiB |      0%      Default |
+-------------------------------+----------------------+----------------------+

+-----------------------------------------------------------------------------+
| Processes:                                                       GPU Memory |
|  GPU       PID   Type   Process name                             Usage      |
|=============================================================================|
|    1    103565      C   /usr/bin/python                            11628MiB |
+-----------------------------------------------------------------------------+
  ```

2. Execute get-pod-from-pid with single PID as an argument, for example:
  ```bash
  $ ./get-pod-from-pid.sh "103565"
  ```

3. Exlanation about output:
  ```bash
  [1st] : parent container process pid (pods pid)
  [2nd] : details of the pod; docker container name and docker process id
  [3rd] : pod container name
  [4th] : pod name  
  [5th] : pod namespace
  ```
