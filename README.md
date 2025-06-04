# tmp-clus25-workshopt

## Overview

This repository contains resources and configurations for the `tmp-clus25-workshopt` project. Below, you'll find the credentials, device details, and a network topology diagram for reference.

## SSH Agent Prerequisites (for Fedora/Linux users)

Before running Ansible or connecting to devices via SSH, ensure your SSH agent is running and your private key is loaded. Run these commands in your terminal (replace the key path if needed):

```bash
eval "$(ssh-agent -s)"
ssh-add ~/.ssh/clus25_workshop_key
```

You must do this each time you start a new terminal session or after a reboot, unless you use a key manager. This is required for SSH authentication to work properly on Fedora/Linux.

## Credentials

- **Username**: `admin`
- **Password**: `C1sco123`

```bash
/home/devnet/DEVWKS-3337
```

## Devices

The following table lists the devices and their corresponding IP addresses:

| **Device Name** | **IP Address** |
| --------------- | -------------- |
| `xrd-1`         | 198.18.158.16  |
| `xrd-2`         | 198.18.158.17  |
| `xrd-3`         | 198.18.158.18  |
| `xrd-4`         | 198.18.158.19  |
| `xrd-5`         | 198.18.158.20  |
| `xrd-6`         | 198.18.158.21  |
| `xrd-7`         | 198.18.158.22  |
| `xrd-8`         | 198.18.158.23  |
| `xrd-9`         | 198.18.158.24  |
| `xrd-10`        | 198.18.158.25  |

## Network Topology

The diagram below illustrates the network topology for this project:

```plaintext
                 xrd-7 (PCE)
                 /        \
              xrd-3 --- xrd-4
               / |        | \
xrd-9 --- xrd-1  |        |  xrd-2 --- xrd-10
               \ |        | /
              xrd-5 --- xrd-6
                 \        /
                 xrd-8 (vRR)
```

## 🧪 Lab Setup Instructions

### Starting XRd Instances

```bash
/root/xrd-tools/scripts/host-check --platform xrd-control-plane --extra-checks docker --extra-checks xr-compose
```

<details>
<summary>OUTPUT</summary>

```bash
root@xrd-host:~# /root/xrd-tools/scripts/host-check --platform xrd-control-plane --extra-checks docker --extra-checks xr-compose
==============================
Platform checks - xrd-control-plane
==============================
PASS -- CPU architecture (x86_64)
PASS -- CPU cores (16)
PASS -- Kernel version (5.4)
PASS -- Base kernel modules
        Installed module(s): dummy, nf_tables
PASS -- Cgroups (v1)
PASS -- Inotify max user instances
        64000 - this is expected to be sufficient for 16 XRd instance(s).
PASS -- Inotify max user watches
        64000 - this is expected to be sufficient for 16 XRd instance(s).
PASS -- Socket kernel parameters (valid settings)
PASS -- UDP kernel parameters (valid settings)
INFO -- Core pattern (core files managed by the host)
PASS -- ASLR (full randomization)
WARN -- Linux Security Modules
        AppArmor is enabled. XRd is currently unable to run with the
        default docker profile, but can be run with
        '--security-opt apparmor=unconfined' or equivalent.
        However, some features might not work, such as ZTP.
PASS -- RAM
        Available RAM is 7.9 GiB.
        This is estimated to be sufficient for 3 XRd instance(s), although memory
        usage depends on the running configuration.
        Note that any swap that may be available is not included.

==============================
Extra checks
==============================

xr-compose checks
-----------------------
PASS -- docker-compose (version 1.25.0)
PASS -- PyYAML (installed)
PASS -- Bridge iptables (disabled)

==================================================================
!! Host NOT set up correctly for xrd-control-plane !!
------------------------------------------------------------------
Extra checks passed: xr-compose
==================================================================
root@xrd-host:~#
```

</details>

From the XRD host (198.18.134.28):

```bash
xr-compose \
  --input-file ~/tmp-clus25-workshopt/xrd/docker-compose.xr.yml \
  --output-file ~/tmp-clus25-workshopt/xrd/docker-compose.yml \
  --image ios-xr/xrd-control-plane:24.2.1
```

```bash
sed -i 's/XR_MGMT_INTERFACES: linux:xr-[0-9]\+/XR_MGMT_INTERFACES: linux:eth0/g' ~/tmp-clus25-workshopt/xrd/docker-compose.yml
```

```bash
sed -i 's/xrd-[0-9]\+-mg0: null/macvlan0: null/g' ~/tmp-clus25-workshopt/xrd/docker-compose.yml
```

```bash
docker-compose -f ~/tmp-clus25-workshopt/xrd/docker-compose.yml up -d
```

### Configuring XRd Instances

From the Ansible VM (198.18.134.29):

```bash
# Enable GRPC on XRD instances
cd ~/tmp-clus25-workshopt/ansible/ && ansible-playbook xrd_apply_config.yaml
```

## Notes

- Try with:
  - `ollama run hermes3`
  - `ollama run qwen3:14b`
  - `ollama run mistral-nemo`
  - `ollama run mixtral:8x7b`
  - Qwen2.5 coder instruct 14b
  - Mistral-small3.1
  - Gemma 3 12b
- test with smaller models like phi for getting arguments for tool calling.
- Useful advice. <https://www.reddit.com/r/n8n/comments/1j25ten/comment/mfpx786/>
- review Berkeley Function-Calling Leaderboard - <https://gorilla.cs.berkeley.edu/leaderboard.html>

```bash
Workshop1  Seat1 ws1-seat1@devnet-events.wbx.ai,
….
Workshop1  Seat16 ws1-seat16@devnet-events.wbx.ai,
Workshop1  Speaker1 ws1-Speaker1@devnet-events.wbx.ai,
Workshop1  Speaker2 ws1-Speaker2@devnet-events.wbx.ai
```

```bash
pass: DevNet_CL1
```
