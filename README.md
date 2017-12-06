# NVML Agent: Install collectors for NVIDIA-GPU across Kubernetes Cluster

> Monitor NVIDIA GPU usage for each container in Kubernetes' pods.

## Prerequisites - jq & Ansible

1. Make sure you have jq:
* Ubuntu
  ```bash
  $ sudo apt-get update && sudo apt-get install jq
  ```
* Mac via brew
  ```bash
  $ brew install jq
  ```

2. Make sure you have [ansible](http://docs.ansible.com/ansible/latest/intro_installation.html) in your machine by issuing this command:
  ```bash
  $ ansible --version
  ```

3. If you don't have ansible in your machine, I encourage you to install via pip (I strongly advise to use ansible 2.2.0)
Install a specific version of ansible:
  ```bash
  $ pip install ansible==2.2.0
  ```

## Trying & Testing the Agent
Go to /scripts dir and find detailed instruction there.

## Prerequisites to Install the Agent

1. Make sure to execute the script in a machine that can list all nodes in your kubernetes cluster
  ```bash
  $ kubectl get nodes
  ```

2. Make sure you can access all machines by **SSH**
  ```bash
  $ ssh [your-node-1]
  ```
Ensure that you have your master public key (.pub file) on authorized_keys file in every node. You need to be able to SSH each node without password.
[Hint](http://www.linuxproblem.org/art_9.html)

## Install the Agent

1. If you just want to install the prerequisites software:
  ```bash
  $ ./install-prerequisites.sh
  ```

2. By default, the prerequisites check will be executed even if you just run the install script:
  ```bash
  $ ./install.sh
  ```

## Starting and Stopping the Agent
Note that the scripts is installed as systemd service.
1. Start the nvml agent:
  ```bash
  $ sudo service nvml_agent start
  ```

1. Stop the nvml agent:
  ```bash
  $ sudo service nvml_agent stop
  ```

## Important Concepts for NVIDIA Utilization in Kubernetes

- [NVIDIA-Driver](http://docs.nvidia.com/cuda/cuda-installation-guide-linux/index.html)
- [Docker-NVIDIA-GPU](https://github.com/NVIDIA/nvidia-docker/wiki)
- [Kubernetes-NVIDIA-GPU](https://kubernetes.io/docs/tasks/manage-gpus/scheduling-gpus/)

Or follow my scripts for installing nvidia driver in ubuntu: [here](https://github.com/sanadhis/kube-ubuntu-utils)

## Maintainer

- Sanadhi Sutandi ([@sanadhis](https://github.com/sanadhis))