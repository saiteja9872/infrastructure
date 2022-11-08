# This script configures a fresh Centos-7 EC2 to be a Jenkins agent node and
# installs the necessary packages for running the Terminal Attention Prioritizer.

# Comment out these specific ssh algorithms so that Jenkins is able to ssh to the agent node.
sed -i 's/^MACs/#MACs/' /etc/ssh/sshd_config
sed -i 's/^KexAlgorithms/#KexAlgorithms/' /etc/ssh/sshd_config
systemctl restart sshd.service

# An agent needs to have a directory dedicated to Jenkins.
mkdir -m 777 -p /var/jenkins

# The following steps are based on the directions from
# https://wiki.viasat.com/display/DABUS/libidb+installation
# and
# https://wiki.viasat.com/display/DABUS/pidb+installation
# for installing libidb and pidb, the libraries needed
# to read from and write to the databus via python.

yum install epel-release -y

yum makecache

yum install java git python-devel java-devel swig libtool zlib zlib-devel gcc make cmake autoconf automake openssl-devel cyrus-sasl-devel rpm-build gcc-c++ doxygen tar uuid jansson-devel libcurl-devel libuuid-devel krb5-workstation cyrus-sasl-gssapi xz-devel python36-pip libffi-devel xz-devel libzstd libidn2 -y

python3.6 -m pip install --upgrade pip

cat <<EOT >> /etc/yum.repos.d/artifactory.repo
[Artifactory]
name=Artifactory
baseurl=https://artifactory.viasat.com/artifactory/databus-rpm/centos7
enabled=1
gpgcheck=0
EOT

yum update -y

yum install -y libidb python36-idb

yum update -y

# Later, we'll need the kerberos config file to be writable.
rm /etc/krb5.conf
touch /etc/krb5.conf
chmod 777 /etc/krb5.conf
