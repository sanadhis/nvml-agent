#!/bin/bash

PLAYBOOK="nvml-agent.yml"
current_dir="$PWD"

NODES=$(kubectl get nodes -o json | jq '.items[] | .status .addresses[] | select(.type=="InternalIP") | .address')

mkdir -p inventory
touch inventory/target
echo "[kube-cluster]" > inventory/target

for node in $NODES
do
    echo $node >> inventory/target
done

ansible-playbook playbooks/$PLAYBOOK \
  -i $PWD/inventory/target \
  -e "target=kube-cluster" \
  -e "current_dir=${current_dir}"