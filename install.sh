#!/bin/bash

set -e

function print-banner () {
    local message="$1"
    echo "################################################################"
    echo "$message"
    echo "################################################################"
}

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
    PLAYBOOK="nvml-agent.yml"
    current_dir="$PWD"

    print-banner "Input hostname address and port for influxdb server"
    read -p "Enter HOSTNAME": influxdb_host
    read -p "Enter PORT(default:8086)": influxdb_port

    print-banner "Input username and password access to write into influxdb server"
    read -p "Enter USERNAME(default:root)": influxdb_user
    read -p "Enter PASSWORD(default:root)": influxdb_pass

    print-banner "Input database to write the statistics for"
    read -p "Enter db name": influxdb_db   

    print-banner "Enter password for sudo privelege in corresponding target nodes"
    ansible-playbook playbooks/$PLAYBOOK \
      -u root \
      -i $PWD/inventory/target \
      -e "target=kube-cluster" \
      -e "current_dir=${current_dir}" \
      -e "influxdb_host=$influxdb_host" \
      -e "influxdb_port=$influxdb_port" \
      -e "influxdb_user=$influxdb_user" \
      -e "influxdb_pass=$influxdb_pass" \
      -e "influxdb_db=$influxdb_db"
      
}

get-hosts
main "$@"