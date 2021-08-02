#!/usr/bin/env python3

from jinja2 import Template
import argparse
import os

head = """version: '3'
services:"""

master_block="""
  mysql_master:
    image: mysql:5.7
    env_file:
      - ./master/mysql_master.env
    container_name: "mysql_master"
    restart: "no"
    ports:
      - 4406:3306
    volumes:
      - ./master/conf/mysql.conf.cnf:/etc/mysql/conf.d/mysql.conf.cnf
      - ./master/data:/var/lib/mysql
    networks:
      - overlay"""

foot = """
networks:
  overlay:"""

def get_port_nr(slave_nr):
    return slave_nr + 4406
def write_docker_compose_file(nr_of_slaves=1):
    with open("./docker-compose.yml.j2", "r") as template_fh:
        slave_tpl = template_fh.read()

    fh = open("./docker-compose.yml", "w")
    fh.write(head)
    fh.write(master_block)
    for i in range(1, nr_of_slaves + 1):
        slave_block = ""
        slave_data = {
                "slave_nr": str(i),
                "external_port_nr": str(get_port_nr(i))
        }
        j2_tpl = Template(slave_tpl)
        slave_block = j2_tpl.render(slave_data)
        fh.write("\n")
        fh.write(slave_block)


    fh.write(foot)
    fh.close()

def prep_slave_dir(slave_nr, root_password, database_name, database_user, database_password):
    slave_nr_str = str(slave_nr)
    slave_dir = "./slave"+slave_nr_str
    os.system("cp -r ./slave " + slave_dir)
    with open("./slave/conf/mysql.conf.cnf.j2", "r") as template_conf_fh:
        slave_tpl = template_conf_fh.read()
    os.system("rm " + slave_dir+"/conf/mysql.conf.cnf.j2")

    slave_conf_fh = open(slave_dir+"/conf/mysql.conf.cnf", "w")
    slave_data = {
            "server_id": str(slave_nr + 1),
            "database_name": database_name
    }
    j2_tpl = Template(slave_tpl)
    slave_conf_str = j2_tpl.render(slave_data)
    slave_conf_fh.write(slave_conf_str)
    slave_conf_fh.close()

    with open("./slave/mysql_slave.env.j2", "r") as template_env_fh:
        slave_env_tpl = template_env_fh.read()
    os.system("rm " + slave_dir+"/mysql_slave.env.j2")
    slave_env_fh = open(slave_dir+"/mysql_slave.env", "w")
    slave_data = {
            "root_password": root_password,
            "database_name": database_name,
            "database_user": database_user,
            "database_password": database_password
    }
    j2_tpl = Template(slave_env_tpl)
    slave_env_str = j2_tpl.render(slave_data)
    slave_env_fh.write(slave_env_str)
    slave_env_fh.close()


def do_all_dirs(nr_of_slaves, root_password, database_name, database_user, database_password):
    os.system("rm -r ./slave[0-9]")
    for i in range(1, nr_of_slaves + 1):
        prep_slave_dir(i, root_password, database_name, database_user, database_password)

def do_master(database_root_password, database_name, database_user, database_password):
    os.system("rm -r ./master")
    os.system("cp -r ./master_tpl ./master")
    with open("./master_tpl/conf/mysql.conf.cnf.j2", "r") as template_conf_fh:
        conf_tpl = template_conf_fh.read()
    os.system("rm ./master/conf/mysql.conf.cnf.j2")
    conf_fh = open("./master/conf/mysql.conf.cnf", "w")
    conf_data = {
            "database_name": database_name
    }
    j2_tpl = Template(conf_tpl)
    conf_str = j2_tpl.render(conf_data)
    conf_fh.write(conf_str)
    conf_fh.close()

    with open("./master_tpl/mysql_master.env.j2", "r") as template_env_fh:
        env_tpl = template_env_fh.read()
    os.system("rm ./master/mysql_master.env.j2")
    env_fh = open("./master/mysql_master.env", "w")
    env_data = {
            "database_root_password": database_root_password,
            "database_name": database_name,
            "database_user": database_user,
            "database_password": database_password
    }
    j2_tpl = Template(env_tpl)
    env_str = j2_tpl.render(env_data)
    env_fh.write(env_str)
    env_fh.close()




    

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-R", "--database-root-password" )
    parser.add_argument("-r", "--slave-root-password" )
    parser.add_argument("-n", "--number-of-slaves" )
    parser.add_argument("-d", "--database-name" )
    parser.add_argument("-U", "--master-database-user" )
    parser.add_argument("-P", "--master-database-password" )
    parser.add_argument("-u", "--slave-database-user" )
    parser.add_argument("-p", "--slave-database-password" )

    args = parser.parse_args()

    if(args.database_root_password is None or args.number_of_slaves is None \
            or args.database_name is None \
            or args.master_database_user is None or args.master_database_password is None):
        exit("Please specify the number of slave instances and a database name!")

    number_of_slaves = int(args.number_of_slaves)
    database_root_password = args.database_root_password
    slave_root_password = args.slave_root_password
    database_name = args.database_name
    master_database_user = args.master_database_user
    master_database_password = args.master_database_password
    slave_database_user = args.slave_database_user
    slave_database_password = args.slave_database_password

    # Making slave values default to master values.
    if slave_root_password == "" or slave_root_password is None:
        slave_root_password = database_root_password
    if slave_database_user == "" or slave_database_user is None:
        slave_database_user = master_database_user
    if slave_database_password == "" or slave_database_password is None:
        slave_database_password = master_database_password

    write_docker_compose_file(number_of_slaves)
    do_master(database_root_password, database_name, master_database_user, master_database_password)
    do_all_dirs(number_of_slaves, slave_root_password, database_name, \
            slave_database_user, slave_database_password)

if __name__ == "__main__":
    main()
