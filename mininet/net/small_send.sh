#!/bin/bash
end=$((SECONDS+60))

if [ "$#" -eq 2 ]; then
	while [ $SECONDS -lt $end ]; do
		socat -u FILE:/root/net/samples/message.txt TCP:$1:8888
		sleep 1
	done
elif [ "$#" -eq 1 ]; then
	while true; do 
		socat -u FILE:/root/net/samples/message.txt TCP:$1:8888
		sleep 1
	done
fi