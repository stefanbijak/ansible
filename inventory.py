#!/home/iptv/ansible/venv/bin/python3

import os
import json
import sys
import pymysql
from dotenv import load_dotenv

load_dotenv()

DB_CONF = {
    "host": os.getenv("DB_HOST"),
    "database": os.getenv("DB_NAME_USERS"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "charset":"utf8mb4",
}

def get_inventory():
    conn = pymysql.connect(**DB_CONF)
    cur = conn.cursor()

    cur.execute(
        """SELECT 'group', hostname, mgmt_ip, username, password FROM ansible_hosts"""
    )

    rows = cur.fetchall()

    inventory = {"_meta":{"hostvars":{}}}

    for group, hostname, mgmt_ip, username, password in rows:
        if group not in inventory:
            inventory[group] = {"hosts": []}
        
        inventory[group]["hosts"].append(hostname)
        
        inventory["_meta"]["hostvars"][hostname] = {  # Dodaj direktno u inventory
            "ansible_host": mgmt_ip,
            "ansible_user": username,
            "ansible_password": password,
        }

    cur.close()
    conn.close()

    return inventory

if __name__ == "__main__":
    if "--list" in sys.argv:
        print(json.dumps(get_inventory(), indent=2))
    elif "--host" in sys.argv:
        print(json.dumps({}))
    else:
        print(json.dumps(get_inventory(), indent=2))