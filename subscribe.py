#! /usr/bin/env python3

import paho.mqtt.client as mqtt
import logging as log
import json
import sys

SUBSCRIBE_CLIENT_NAME = None

# Initiating logging
log.basicConfig(filename='cloud.log', filemode='a', level=log.INFO, format="[%(asctime)s] %(levelname)s %(message)s", datefmt='%d-%m-%Y %I:%M:%S %p')

def on_message(client, userdata, message):
	payload = message.payload.decode('UTF-8')
	
	log.info(f"[{SUBSCRIBE_CLIENT_NAME}]: Payload recieved.")
	with open('signed_url.json','w') as file:
		file.write(payload)
		file.close()

	log.info(f"[{SUBSCRIBE_CLIENT_NAME}]: Disconnecting....")
	client.disconnect()

def on_connect(client, userdata, flags, rc):
	if rc == 0:
		log.info(f"[{SUBSCRIBE_CLIENT_NAME}]: Connected!")
		
	else:
		log.warning(f"[{SUBSCRIBE_CLIENT_NAME}]: Could not establish connection.")
		sys.exit(1)


def start_subscribe(broker, port, interval, client_name, topic, qos, root_ca, device_cert, private_key):
	global SUBSCRIBE_CLIENT_NAME
	SUBSCRIBE_CLIENT_NAME = client_name

	SubClient = mqtt.Client(client_name)
	SubClient.tls_set(root_ca, device_cert, private_key)

	SubClient.on_connect = on_connect
	SubClient.on_message = on_message

	try:
		SubClient.connect(broker, port, interval)
		SubClient.subscribe(topic, qos)
	except Exception as e:
		log.INFO(f"Could not run subscribe client.")
		log.ERROR(e)
		sys.exit(1)

	SubClient.loop_forever()