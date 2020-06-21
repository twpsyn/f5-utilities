#!python3

from f5.bigip import ManagementRoot
import getpass


class F5_Item:
    def __init__(self, name):
        self.name = name
        self.usage = []

    def add_usage(self, usage):
        self.usage.append(usage)

    def get_usage(self):
        return self.usage

    def get_usage_str(self):
        outstr = ":"
        for use in self.usage:
            outstr = outstr + "\n\t* " + use
        return outstr

    @property
    def is_used(self):
        if len(self.usage) == 0:
            return False
        else:
            return True


device = input("Device: ")
user = input("Username: ")
passwd = getpass.getpass("Password: ")

print("")

f5 = ManagementRoot(device, user, passwd)

nodelist = {}
poollist = {}

print("**** DISCOVERY ****")

nodes = f5.tm.ltm.nodes.get_collection()
for node in nodes:
    print(f"Discovered node: {node.fullPath}")
    nodelist[node.fullPath] = F5_Item(node.fullPath)

pools = f5.tm.ltm.pools.get_collection()
for pool in pools:
    print(f"Discovered pool: {pool.fullPath}")
    poollist[pool.fullPath] = F5_Item(pool.fullPath)
    for member in pool.members_s.get_collection():
        nodelist[member.fullPath.split(":")[0]].add_usage(pool.fullPath)

virtuals = f5.tm.ltm.virtuals.get_collection()
for virt in virtuals:
    print(f"Discovered virtual server: {virt.fullPath}")
    try:
        vs_pool = virt.pool
    except AttributeError:  # virtual server has no pool (L2 forwarding for example)
        print(f" Virtual server {virt.fullPath} has no pool")
        continue
    poollist[vs_pool].add_usage(virt.fullPath)

print("\n**** ANALYSIS ****")

print("Unused Items:")
at_least_one_unused = False
for k in nodelist:
    if not nodelist[k].is_used:
        print(f"Node {k} is unused")
        at_least_one_unused = True
for k in poollist:
    if not poollist[k].is_used:
        print(f"Pool {k} is unused")
        at_least_one_unused = True

if not at_least_one_unused:
    print("No unused items")

print("")
print("Item Usage:")
for k in nodelist:
    if nodelist[k].is_used:
        print(f"Node {k} is in use in pools{nodelist[k].get_usage_str()}")
for k in poollist:
    if poollist[k].is_used:
        print(f"Pool {k} is in use in virtual servers{poollist[k].get_usage_str()}")
