#!/usr/bin/env python3

import argparse
import os
from jinja2 import Template

def create_user(username, password, host, privileges, root_pw, port=3306, permissive=False, protocol_arg=""):
    if permissive:
        mysql_file_name = "./mysql_user_add_permissive.sql"
    else:
        mysql_file_name = "./mysql_user_add.sql"
    with open(mysql_file_name+".j2", "r") as mysql_tpl_fh:
        mysql_tpl = mysql_tpl_fh.read()

    os.system("rm " + mysql_file_name)

    with open(mysql_file_name, "w") as mysql_fh:
        tpl_data = {
                "username": username,
                "password": password,
                "host": host,
                "privileges": privileges
        }
        j2_tpl = Template(mysql_tpl)
        mysql_user = j2_tpl.render(tpl_data)
        mysql_fh.write(mysql_user)
    cmd = "mysql -u root -p{root_pw} --host={host} --port={port} {protocol_arg} --force < {mysql_file_name}".format( \
            root_pw=root_pw, host=host, port=port, protocol_arg=protocol_arg, mysql_file_name=mysql_file_name)
    os.system(cmd)

# This assumes replicas on Docker on localhost, with contiguous port range open, starting with master on port 4406
def create_user_everywhere(nr_of_slaves, username, password, host, privileges, master_pw, slave_pw, permissive=False):
    # The master
    create_user(username, password, host, privileges, master_pw, 4406, permissive, "--protocol=TCP")
    nr_of_slaves = int(nr_of_slaves)
    for i in range(1, nr_of_slaves+1):
        port = i + 4406
        create_user(username, password, host, privileges, slave_pw, port, permissive, "--protocol=TCP")

def main():

    parser = argparse.ArgumentParser()
    parser.add_argument("-n", "--number-of-slaves")
    parser.add_argument("-u", "--database-user")
    parser.add_argument("-p", "--database-password")
    parser.add_argument("-H", "--host", default="127.0.0.1")
    parser.add_argument("-P", "--privileges")
    parser.add_argument("-M", "--master-password")
    parser.add_argument("-S", "--slave-password")
    parser.add_argument("-e", "--permissive", action="store_true")

    args = parser.parse_args()


    number_of_slaves = int(args.number_of_slaves)
    database_user = args.database_user
    database_password = args.database_password
    host = args.host
    privileges = args.privileges
    master_password = args.master_password
    slave_password = args.slave_password
    permissive = args.permissive

    if slave_password is None:
        slave_password = master_password

    create_user_everywhere(number_of_slaves, database_user, database_password, host, privileges, master_password, slave_password, permissive)

if __name__ == "__main__":
    main()
