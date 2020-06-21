# Virt_Enable_Disable

My goal here was to try creating a python script to replace an Ansible playbook which takes longer to do the job than I'd like. I'm quite happy with the result.

## Background

### The Scenario

At my job we have a client where every month we need to shut down virtual servers on their F5 LTMs in order for them to perform scheduled maintenance on the servers. Once the maintenance is complete we need to bring the virtual servers back up. It's a simple enough task, but one ripe for a bit of automation.

They have two environments - a production and a pre-production. The production is clustered, the pre-production is not. So the automation needs to account for that and in the cluster make the change only on one device, then sync the cluster up. By convention you would make changes on the currently active device and synchronise that to the others, but in reality changes can be made on any cluster member and synced.

There are also front-end and back-end F5s in both environments, so we need to make changes in two places.

### Ansible

My initial shot at automating the process was to write some ansible playbooks. 

There are two playbooks per environment, one to disable and one to enable. F5s are defined in groups for frontend and back-end in the inventory, and group_vars are set up for the virtual servers to modify in each.

For the production environment with the cluster, the ansible playbook has to pick one F5 to make the change on. It does that with a task to look for the active device. All other devices are then skipped for the remaining tasks.

The playbooks work, but they're a little slow. I sometimes feel like I could do the tasks manually in less time. That's not ideal, even though I preach that automation isn't necessarily about being quicker, it's also about repeatability and reducing human error.

### Python

As the Ansible playbooks felt a little slow, I thought it would be a nice challenge to write a python script utilising the F5 SDK library to run the automation instead.

The script needed to work for both disabling and enabling the virtual servers, and for either environment by way of an input file (I like YAML for these things, but JSON would be an option).

## Implementation

I'm not going to claim that what I wrote is perfect, it's quite hacky, but it does the job and in my lab it does it quickly.

Usage for the script (from the argparse output) is:

```
usage: virt_enable_disable.py [-h] [-e | -d] filename

Script to enable or disable virtual servers on F5 BIG-IPs.

positional arguments:
  filename       YAML file containing devices and virtual servers

optional arguments:
  -h, --help     show this help message and exit
  -e, --enable   Enable virtual servers
  -d, --disable  Disable virtual servers

If neither enable nor disable are specified then the default action is to
print the current status of the virtual servers.
```

The YAML file is the only required argument. It should contain a list of dictionaries which define the clusters and virtual servers in each.