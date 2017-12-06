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
    ansible \
        -i inventory/target kube-cluster \
        -m ping -u root      
}

get-hosts
main "$@"