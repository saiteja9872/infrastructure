# The following vars are env variables from the Jekins job
# CERT_NAME, CERT_URL, CERT_MD5, host
# The password for the DB is a secret file bound to the jenkins job

# Delete all blackbox notifications older than this number of days.
DAYS_TO_KEEP=50

# Cert file
CERT_FILE="./${CERT_NAME}"

# Make sure postgresql and postgresql client are installed.
if ! [ -x "$(command -v psql)" ]; then
	sudo yum -y install https://download.postgresql.org/pub/repos/yum/reporpms/EL-7-x86_64/pgdg-redhat-repo-latest.noarch.rpm
	sudo yum -y install postgresql95
fi

# Check if Cert exists
if [ -f "$CERT_FILE" ]; then 
	echo "Cert exists. Will verify md5"
else
	echo "Cert does not exist. Will download and verify md5"
	wget -O "$CERT_FILE" "${CERT_URL}"
fi        
# Verify md5 sum
if [ "$(md5sum < $CERT_FILE)" = "${CERT_MD5}  -" ]; then
	echo "MD5 matches"
else
	echo "MD5 mismatch. Will get 'SSL error' when connecting to DB"
fi

# This is the query we'll use to select all bb notifications
# that are older than the desired number of days.
expired_bb_query () {
    psql \
        -qtAX \
        -h ${host} -p 5432 \
        "user=${environment}_bbserver_db_admin dbname=devops_${environment}_bbserver_db sslrootcert=$CERT_FILE sslmode=verify-full"\
        -c "$1 FROM bbmanager_blackbox WHERE event_time < (now() - '$DAYS_TO_KEEP days'::interval);"
}

# Count how many bb notifications are expired.
NUM_EXPIRED=$( expired_bb_query "SELECT COUNT(*)" )
if [ $NUM_EXPIRED -eq 0 ]; then
    printf "\n%s\n%s\n%s\n\n" \
        "------------------------------------------------------------------------------------------" \
        "There were no blackbox notifications older than $DAYS_TO_KEEP days on the $environment bbserver. "\
        "------------------------------------------------------------------------------------------"
else
    # Record the names of all the expired bb notifications.
    expired_bb_query "SELECT name"

    # Delete the expired bb notifications.
    expired_bb_query "DELETE"

    # If all goes well, print out the number of bb notifications that were deleted.
    printf "\n%s\n%s\n%s\n\n" \
        "----------------------------------------------------------------------------------------------" \
        "Successfully deleted $NUM_EXPIRED blackbox notifications older than $DAYS_TO_KEEP days from $environment bbserver. "\
        "----------------------------------------------------------------------------------------------"
fi

