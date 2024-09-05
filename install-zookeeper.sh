wget https://dlcdn.apache.org/zookeeper/zookeeper-3.9.2/apache-zookeeper-3.9.2-bin.tar.gz

tar -xzf apache-zookeeper-3.9.2-bin.tar.gz
sudo mv apache-zookeeper-3.9.2-bin /usr/local/zookeeper
sudo mkdir /var/lib/zookeeper
sudo cp /usr/local/zookeeper/conf/zoo_sample.cfg /usr/local/zookeeper/conf/zoo.cfg
dataDir=/var/lib/zookeeper

sudo /usr/local/zookeeper/bin/zkServer.sh start
 ## sudo /usr/local/zookeeper/bin/zkServer.sh start-foreground
