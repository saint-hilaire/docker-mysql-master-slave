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

def prep_slave_dir(slave_nr, database_name):
    slave_nr_str = str(slave_nr)
    slave_dir = "./slave"+slave_nr_str
    os.system("cp -r ./slave " + slave_dir)
    os.system("rm " + slave_dir+"/conf/mysql.conf.cnf.j2")
    with open("./slave/conf/mysql.conf.cnf.j2", "r") as template_conf_fh:
        slave_tpl = template_conf_fh.read()

    slave_conf_fh = open(slave_dir+"/conf/mysql.conf.cnf", "w")
    slave_data = {
            "server_id": str(slave_nr + 1),
            "database_name": database_name
    }
    j2_tpl = Template(slave_tpl)
    slave_conf_str = j2_tpl.render(slave_data)
    slave_conf_fh.write(slave_conf_str)
    slave_conf_fh.close()

def do_all_dirs(nr_of_slaves, database_name):
    os.system("rm -r ./slave[0-9]")
    for i in range(1, nr_of_slaves + 1):
        prep_slave_dir(i, database_name)

def do_master(database_name, database_user, database_password):
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
    parser.add_argument("-n", "--number-of-slaves" )
    parser.add_argument("-d", "--database-name" )
    parser.add_argument("-u", "--database-user" )
    parser.add_argument("-p", "--database-password" )

    args = parser.parse_args()

    if(args.number_of_slaves is None or args.database_name is None \
            or args.database_user is None or args.database_password is None):
        exit("Please specify the number of slave instances and a database name!")

    number_of_slaves = int(args.number_of_slaves)
    database_name = args.database_name
    database_user = args.database_user
    database_password = args.database_password

    write_docker_compose_file(number_of_slaves)
    do_master(database_name, database_user, database_password)
    do_all_dirs(number_of_slaves, database_name)

if __name__ == "__main__":
    main()
