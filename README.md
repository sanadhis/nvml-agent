# NVML Agent: Install collectors for NVIDIA-GPU across Kubernetes Cluster

> Monitor NVIDIA GPU usage for each container in Kubernetes' pods.

## Prerequisites - jq & Ansible

1. Make sure you have jq:
  ```bash
  $ sudo apt-get update && sudo apt-get install jq
  ```

2. Make sure you have [ansible](http://docs.ansible.com/ansible/latest/intro_installation.html) in your machine by issuing this command:
  ```bash
  $ ansible --version
  ```

3. If you don't have ansible in your machine, I encourage you to install via pip:
  ```bash
  $ pip install ansible
  ```
  or install a specific version of ansible
  ```bash
  $ pip install ansible==2.2.0
  ```

## Prerequisites - Usage

1. Make sure to execute the script in a machine that can list all nodes in your kubernetes cluster
  ```bash
  $ kubectl get nodes
  ```

2. Make sure you can access all machines by SSH
  ```bash
  $ ssh [your-node-1]
  ```

## Usage

1. If you just want to install the prerequisites software:
  ```bash
  $ ./install-prerequisites.sh
  ```

2. By default, the prerequisites check will be executed even if you just run the install script:
  ```bash
  $ ./install.sh
  ```

## Maintainer

- Sanadhi Sutandi ([@sanadhis](https://github.com/sanadhis))