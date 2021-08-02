#!/bin/bash

# d: database name
# n: number of slaves
while getopts R:r:d:n:U:P:u:p: flag
do
    case "${flag}" in
        R) database_root_password=${OPTARG};;
        r) slave_root_password=${OPTARG};;
        d) database_name=${OPTARG};;
        n) number_of_slaves=${OPTARG};;
        U) master_database_user=${OPTARG};;
        P) master_database_password=${OPTARG};;
        u) slave_database_user=${OPTARG};;
        p) slave_database_password=${OPTARG};;
    esac
done

if [[ "$database_root_password" == "" ]] || [[ "$database_name" == "" ]] || [[ "$number_of_slaves" == "" ]] || [[ "$master_database_user" == "" ]] || [[ "$master_database_password" == "" ]]
then
	echo "Please specify a database root password (-R), a database name (-d) and the number of slave instances (-n) and also database user and password for the master node (-U, -P)"
	exit
fi

# Make slave parameters default to master values
if [[ "$slave_root_password" == "" ]]
then
	slave_root_password=$database_root_password
fi
if [[ "$slave_database_user" == "" ]]
then
	slave_database_user=$master_database_user
fi
if [[ "$slave_database_password" == "" ]]
then
	slave_database_password=$master_database_password
fi

./dynamic_docker_compose.py -R $database_root_password -r $slave_root_password -d $database_name -n $number_of_slaves -U $master_database_user -P $master_database_password -u $slave_database_user -p $slave_database_password

docker-compose down
rm -rf ./master/data/*
rm -rf ./slave/data/*
docker-compose build
docker-compose up -d

until docker exec mysql_master sh -c "export MYSQL_PWD=$database_root_password; mysql -u root -e \";\""
do
    echo "Waiting for mysql_master database connection..."
    sleep 4
done

priv_stmt="GRANT REPLICATION SLAVE ON *.* TO \"$slave_database_user\"@\"%\" IDENTIFIED BY \"$slave_database_password\"; FLUSH PRIVILEGES;"
docker exec mysql_master sh -c "export MYSQL_PWD=$database_root_password; mysql -u root -e '$priv_stmt'"

for((i=1; i <= $number_of_slaves; i++))
do
	until docker-compose exec mysql_slave$i sh -c "export MYSQL_PWD=$slave_root_password; mysql -u root -e \";\""
	do
	    echo "Waiting for mysql_slave$i database connection..."
	    sleep 4
	done

	docker-ip() {
	    docker inspect --format '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' "$@"
	}

	MS_STATUS=`docker exec mysql_master sh -c "export MYSQL_PWD=$database_root_password; mysql -u root -e \"SHOW MASTER STATUS\""`
	CURRENT_LOG=`echo $MS_STATUS | awk '{print $6}'`
	CURRENT_POS=`echo $MS_STATUS | awk '{print $7}'`

	start_slave_stmt="CHANGE MASTER TO MASTER_HOST='$(docker-ip mysql_master)',MASTER_USER='$slave_database_user',MASTER_PASSWORD='$slave_database_password',MASTER_LOG_FILE='$CURRENT_LOG',MASTER_LOG_POS=$CURRENT_POS; START SLAVE;"
	start_slave_cmd="export MYSQL_PWD=$slave_root_password; mysql -u root -e \""
	start_slave_cmd+="$start_slave_stmt"
	start_slave_cmd+='"'
	docker exec mysql_slave$i sh -c "$start_slave_cmd"

	docker exec mysql_slave$i sh -c "export MYSQL_PWD=$slave_root_password; mysql -u root -e 'SHOW SLAVE STATUS \G'"
done
