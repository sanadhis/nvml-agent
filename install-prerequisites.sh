#!/bin/bash

set -e

function get-hosts () {
    nodes=$(kubectl get nodes -o json | jq '.items[] | .status .addresses[] | select(.type=="InternalIP") | .address')

    mkdir -p inventory
    touch inventory/target
    echo "[kube-cluster]" > inventory/target

    for node in $nodes
    do
        echo $node >> inventory/target
    done
}

function main () {
    PLAYBOOK="prerequisites.yml"
    current_dir="$PWD"

    ansible-playbook playbooks/$PLAYBOOK \
      -i $PWD/inventory/target \
      -e "target=kube-cluster" \
      -e "current_dir=${current_dir}"
}

get-hosts
main "$@"