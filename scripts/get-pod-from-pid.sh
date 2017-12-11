#!/bin/bash
# the script requires pid of a process that runs on GPU.
# to check the process pid, issue "nvidia-smi" in shell terminal
pid="$1"

# use pstree to find parent container (pod) of a spefic container pid in kubernetes
# docker-containerd-shim usually the 4th children of systemd process; 1+4 = 5
pod_pid=$(pstree -sg $pid | awk -F "[()]" '{ for (i=2; i<NF; i+=2) print $i }' | sed -n '5 p')

# print pod's pid
echo $pod_pid

# After we find the pid of pod, now we inspect docker ps -q to find details of the pod
# we want to look for docker process name {{.Name}} especially because they contains: container name, pod namespace, and pod name
docker_process=$(docker ps -q | xargs docker inspect --format '{{printf "%.0f %s %s" .State.Pid .Name .Id}}' | grep "^$pod_pid")

# print docker process' details
echo $docker_process

# construct an array, delimited by space char
docker_process=($docker_process)

# obtain pod pid, details (docker process name), and container id
pod_pid=${docker_process[@]:0:1}
pod_details=${docker_process[@]:1:1}
container_id=${docker_process[@]:2:1}

# Notes:
# make sure pod_pid is equal to pid we get from nvidia-smi command
# we can use container_id to recheck whether we get the exact pod or not
# to perform additional check on container_id execute this command in master node of your kubernetes cluster: 
# kubectl get pod $pod_name --namespace=$namespace_name -o yaml | grep containerID

# The name format for each running pod process in kubernetes is as follows:
# /k8s_[pod-name]_[container_name]_[pod_namespace]_[random_hash]
# So we split them based on '_' to obtain pod's container_name, pod_name, and pod_namespace
pod_container_name=$(echo $pod_details | cut -d _ -f 2)
pod_name=$(echo $pod_details | cut -d _ -f 3)
namespace_name=$(echo $pod_details | cut -d _ -f 4)

# print pod's container name, pod name, and pod namespace
echo $pod_container_name
echo $pod_name
echo $namespace_name