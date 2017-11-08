#!/bin/bash
pod_pid="$1"

docker_process=$(docker ps -q | xargs docker inspect --format '{{.State.Pid}} {{.Name}} {{.Id}}' | grep "^$pod_pid")

echo $pod_pid
echo $docker_process

# construct an array
docker_process=($docker_process)

pod_pid=${docker_process[@]:0:1}
pod_details=${docker_process[@]:1:1}
container_id=${docker_process[@]:2:1}

container_name=$(echo $pod_details | cut -d _ -f 2)
pod_name=$(echo $pod_details | cut -d _ -f 3)
namespace_name=$(echo $pod_details | cut -d _ -f 4)

# kubectl get pod $pod_name --namespace=$namespace_name -o yaml | grep containerID

echo $container_name
echo $pod_name
echo $namespace_name