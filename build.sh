#!/bin/bash

# d: database name
# n: number of slaves
while getopts d:n:u:p: flag
do
    case "${flag}" in
        d) database_name=${OPTARG};;
        n) number_of_slaves=${OPTARG};;
        u) database_user=${OPTARG};;
        p) database_password=${OPTARG};;
    esac
done

if [[ "$database_name" == "" ]] || [[ "$number_of_slaves" == "" ]] || [[ "$database_user" == "" ]] || [[ "$database_password" == "" ]]
then
	echo "Please specify a database name (-d) and the number of slave instances (-n) and also database user and password (-u, -p)"
	exit
fi

./dynamic_docker_compose.py -d $database_name -n $number_of_slaves -u $database_user -p $database_password

docker-compose down
rm -rf ./master/data/*
rm -rf ./slave/data/*
docker-compose build
docker-compose up -d

until docker exec mysql_master sh -c 'export MYSQL_PWD=111; mysql -u root -e ";"'
do
    echo "Waiting for mysql_master database connection..."
    sleep 4
done

priv_stmt='GRANT REPLICATION SLAVE ON *.* TO "mydb_slave_user"@"%" IDENTIFIED BY "mydb_slave_pwd"; FLUSH PRIVILEGES;'
docker exec mysql_master sh -c "export MYSQL_PWD=111; mysql -u root -e '$priv_stmt'"

for((i=1; i <= $number_of_slaves; i++))
# for i in {1..$nr_of_slaves}
do
	until docker-compose exec mysql_slave$i sh -c 'export MYSQL_PWD=111; mysql -u root -e ";"'
	do
	    echo "Waiting for mysql_slave$i database connection..."
	    sleep 4
	done

	docker-ip() {
	    docker inspect --format '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' "$@"
	}

	MS_STATUS=`docker exec mysql_master sh -c 'export MYSQL_PWD=111; mysql -u root -e "SHOW MASTER STATUS"'`
	CURRENT_LOG=`echo $MS_STATUS | awk '{print $6}'`
	CURRENT_POS=`echo $MS_STATUS | awk '{print $7}'`

	start_slave_stmt="CHANGE MASTER TO MASTER_HOST='$(docker-ip mysql_master)',MASTER_USER='mydb_slave_user',MASTER_PASSWORD='mydb_slave_pwd',MASTER_LOG_FILE='$CURRENT_LOG',MASTER_LOG_POS=$CURRENT_POS; START SLAVE;"
	start_slave_cmd='export MYSQL_PWD=111; mysql -u root -e "'
	start_slave_cmd+="$start_slave_stmt"
	start_slave_cmd+='"'
	docker exec mysql_slave$i sh -c "$start_slave_cmd"

	docker exec mysql_slave$i sh -c "export MYSQL_PWD=111; mysql -u root -e 'SHOW SLAVE STATUS \G'"
done
