import ipaddress
import json
import glob
import os
import mysql.connector
from dotenv import load_dotenv

load_dotenv()

def normalize_server_group(name):
    return str(name.lower().replace(' ', '').strip())

mgmt_subnet = ipaddress.ip_network("10.152.0.0/24")

try:
    mydb = mysql.connector.connect(
        host=os.getenv("DB_HOST"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME_USERS"),
    )

    if mydb.is_connected():
        print("CONNECTED")
        cursor = mydb.cursor()
        
        # Dohvatanje VLAN-ova (sada čuvamo i ID)
        cursor.execute("SELECT id, name, subnet FROM vlans")
        result = cursor.fetchall()
        networks = []
        for net in result:
            networks.append({
                "id": net[0],
                "name": net[1],
                "subnet": ipaddress.ip_network(net[2])
            })

        # Dohvatanje grupa
        cursor.execute("SELECT id, name FROM server_groups;")
        sg_res = cursor.fetchall()
        sg_map = {normalize_server_group(sg[1]): sg[0] for sg in sg_res}

        # Učitavanje JSON fajlova
        host_ips = []
        for name in glob.glob("./update_test/*.json"):
            with open(name, 'r') as file:
                data = json.load(file)
            host_ips.append({
                "hostname": data["hostname"], 
                "group": data["groups"][0], 
                "ips": data["ips"],
                "uptime": data["uptime"]
            })

        for host in host_ips:
            found_mgmt_ips = []
            # Lista: [{"ip": "x.x.x.x", "vlan_id": 3}, ...]
            found_vlan_ips = []

            for ip_str in host["ips"]:
                ip = ipaddress.ip_address(ip_str)
                
                if ip in mgmt_subnet:
                    found_mgmt_ips.append(ip)
                    print(f"  [MGMT] {ip} -> {host['hostname']}")
                else:
                    # Provjera ostalih VLAN-ova
                    for net in networks:
                        if ip in net["subnet"]:
                            found_vlan_ips.append({
                                "ip": str(ip),
                                "vlan_id": net["id"],
                                "vlan_name": net["name"]
                            })
                            print(f"  [VLAN:{net['name']}] {ip} -> {host['hostname']}")
                            break  # IP može biti samo u jednom VLAN-u

            # Normalizacija grupe
            norm_group = normalize_server_group(host["group"])
            group_id = sg_map.get(norm_group)

            if not group_id:
                print(f"Preskačem {host['hostname']} - grupa '{host['group']}' ne postoji u bazi.")
                continue

            # ── Upisivanje servera u bazu ──────────────────────────────────────

            if len(found_mgmt_ips) > 1:
                print(f"[{host['hostname']}] Više MGMT IP-ova, upisujem bez mgmt_ip kolone...")

                upsert_server = """
                    INSERT INTO servers (group_id, hostname, status, ssh_port, uptime) 
                    VALUES (%s, %s, 'online', 22, %s)
                    ON DUPLICATE KEY UPDATE group_id = VALUES(group_id), uptime = VALUES(uptime)
                """
                cursor.execute(upsert_server, (int(group_id), host["hostname"], int(host["uptime"])))
                mydb.commit()

                cursor.execute("SELECT id FROM servers WHERE hostname = %s", (host["hostname"],))
                server_db_id = cursor.fetchone()[0]

                # Upis više MGMT IP-ova u server_mgmt_ips
                mgmt_ips_query = """
                    INSERT IGNORE INTO server_mgmt_ips (server_id, ip_address, label) 
                    VALUES (%s, %s, %s)
                """
                for i, ip_addr in enumerate(found_mgmt_ips):
                    cursor.execute(mgmt_ips_query, (server_db_id, str(ip_addr), f"MGMT_{i+1}"))
                mydb.commit()

            elif len(found_mgmt_ips) == 1:
                print(f"[{host['hostname']}] Jedna MGMT IP adresa: {found_mgmt_ips[0]}")

                query = """
                    INSERT INTO servers (group_id, hostname, mgmt_ip, status, ssh_port, uptime) 
                    VALUES (%s, %s, %s, 'online', 22, %s)
                    ON DUPLICATE KEY UPDATE 
                    group_id = VALUES(group_id),
                    mgmt_ip = VALUES(mgmt_ip),
                    status = 'online',
                    uptime = VALUES(uptime)
                """
                try:
                    cursor.execute(query, (int(group_id), host["hostname"], str(found_mgmt_ips[0]), int(host["uptime"])))
                    mydb.commit()
                    print(f"  Upisan server: {host['hostname']} (grupa ID: {group_id})")
                except mysql.connector.Error as err:
                    print(f"  Greška pri upisu servera {host['hostname']}: {err}")
                    continue

                cursor.execute("SELECT id FROM servers WHERE hostname = %s", (host["hostname"],))
                server_db_id = cursor.fetchone()[0]

            else:
                print(f"[{host['hostname']}] Nema MGMT IP adrese, preskačem.")
                continue

            # ── Upisivanje VLAN IP adresa u server_ips ────────────────────────

            if found_vlan_ips:
                vlan_ip_query = """
                    INSERT IGNORE INTO server_ips (server_id, vlan_id, ip_address)
                    VALUES (%s, %s, %s)
                """
                for entry in found_vlan_ips:
                    try:
                        cursor.execute(vlan_ip_query, (server_db_id, entry["vlan_id"], entry["ip"]))
                        print(f"  [server_ips] {entry['ip']} -> VLAN '{entry['vlan_name']}' (ID: {entry['vlan_id']})")
                    except mysql.connector.Error as err:
                        print(f"  Greška pri upisu IP {entry['ip']}: {err}")
                
                mydb.commit()
                print(f"  Upisano {len(found_vlan_ips)} VLAN IP adresa za {host['hostname']}.")
            else:
                print(f"  [{host['hostname']}] Nema IP adresa koje odgovaraju poznatim VLAN-ovima.")

except Exception as e:
    print(f"Greška u radu: {e}")