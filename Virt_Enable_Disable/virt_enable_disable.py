#!/usr/bin/python3
import argparse
import yaml
import getpass
from f5.bigip import ManagementRoot
from f5.utils.responses.handlers import Stats
from time import sleep
from requests.exceptions import HTTPError, ConnectionError


def connect(devs, user, password):
    if type(devs) is not list:
        mgmt = ManagementRoot(devs, user, password)
        return mgmt
    else:
        for dev in devs:
            print(f"Attempting to connect to {dev}")
            try:
                mgmt = ManagementRoot(dev, user, password)
            except HTTPError as e:
                print(
                        "HTTPError: Received HTTP Error "
                        f"{e.response.status_code} - {e.response.reason}."
                    )
                if e.response.status_code == 401:
                    print("\nAuthentication failed. Aborting.")
                    print("Please check username and password.\n")
                    exit(1)
                else:
                    next
            except ConnectionError:
                print("ConnectionError: Unable to connect.")
                next
            except Exception:
                print(f"Exception: Unhandled exception when connecting to {dev}.")
                next
            else:
                print("Connected.")
                return mgmt
        print("\nUnable to connect to any device.")
        print("Check device statuses, dns resolution, and credentials.\n")
        exit(1)


def print_states(virtual_servers):
    print("")
    print("Virtual Server states:")
    for virt in virtual_servers:
        myvirt = mgmt.tm.ltm.virtuals.virtual.load(name=virt)
        if myvirt.to_dict().get("enabled"):
            confstate = "Enabled"
        elif myvirt.to_dict().get("disabled"):
            confstate = "Disabled"
        else:
            confstate = "UNKNOWN"

        virtstats = Stats(myvirt.stats.load())
        operstate = virtstats.stat['status_availabilityState']['description']

        print(f"- {virt}: {confstate} ({operstate})")
    print("")


def sync(datagroup):
    print("Synchronising")
    mgmt.tm.cm.exec_cmd("run", utilCmdArgs=f"config-sync to-group {datagroup}")

    wait = 0
    while get_sync_status(mgmt) != "green" and wait < 12:
        wait += 1
        sleep(0.5 * wait)
    print(f"Sync status: {get_sync_status(mgmt)}")


def get_sync_status(mgmt):
    sstate = mgmt.tm.cm.sync_status.load()
    return sstate.entries["https://localhost/mgmt/tm/cm/sync-status/0"]["nestedStats"][
        "entries"
    ]["color"]["description"]


def enable_virts(virtual_servers):
    for virt in virtual_servers:
        print(f"Enabling {virt}")
        myvirt = mgmt.tm.ltm.virtuals.virtual.load(name=virt)
        myvirt.enabled = True
        myvirt.update()


def disable_virts(virtual_servers):
    for virt in virtual_servers:
        print(f"Disabling {virt}")
        myvirt = mgmt.tm.ltm.virtuals.virtual.load(name=virt)
        myvirt.disabled = True
        myvirt.update()


def get_args():
    parser = argparse.ArgumentParser()
    parser.description = "Script to enable or disable virtual servers on F5 BIG-IPs."
    parser.epilog = (
        "If neither enable nor disable are specified then the default "
        "action is to print the current status of the virtual servers."
    )
    parser.add_argument(
        "filename", type=str, help="YAML file containing devices and virtual servers"
    )
    action = parser.add_mutually_exclusive_group()
    action.add_argument(
        "-e", "--enable", action="store_true", help="Enable virtual servers"
    )
    action.add_argument(
        "-d", "--disable", action="store_true", help="Disable virtual servers"
    )
    return parser.parse_args()


if __name__ == "__main__":

    args = get_args()

    if not (args.enable or args.disable):
        printonly = True
    else:
        printonly = False

    try:
        with open(args.filename, "r") as f:
            groups = yaml.safe_load(f)
    except (FileNotFoundError, PermissionError) as e:
        print(e)
        exit(2)
    except Exception as e:
        print(f"Unexpected error opening file {args.filename}: ")
        print(e)
        exit(2)

    os_user = getpass.getuser()
    username = input(f"Enter username [{os_user}]: ") or os_user
    password = getpass.getpass("Enter password: ")
    print()

    for cluster in groups:
        mgmt = connect(cluster["devs"], username, password)

        if len(cluster["devs"]) > 1:
            s_status = get_sync_status(mgmt)
            print(f"\nSync status: {s_status}")

            if not printonly:
                if s_status != "green":
                    print("\nCluster is not synchronised. Please check sync status.\n")
                    exit(1)

        print_states(cluster["virts"])

        if args.enable:
            enable_virts(cluster["virts"])
        if args.disable:
            disable_virts(cluster["virts"])

        if not printonly:
            print_states(cluster["virts"])

            if len(cluster["devs"]) > 1:
                sync(cluster["dgrp"])

            print("\n")
