# NVML Agent: Install collectors for NVIDIA-GPU across Kubernetes Cluster

> Monitor NVIDIA GPU usage for each container in Kubernetes' pods.

## Prerequisites - jq & Ansible

1. Make sure you have jq:
  ```bash
  $ sudo apt-get update && sudo apt-get install jq
  ```

2. Make sure you have [ansible](http://docs.ansible.com/ansible/latest/intro_installation.html) in your machine by issuing this command:
  ```bash
  $ ansible -V
  ```

3. If you don't have ansible in your machine, I encourage you to install via pip:
  ```bash
  $ pip install ansible
  ```
  or install a specific version of ansible
  ```bash
  $ pip install ansible==2.2.0
  ```

## Maintainer

- Sanadhi Sutandi ([@sanadhis](https://github.com/sanadhis))