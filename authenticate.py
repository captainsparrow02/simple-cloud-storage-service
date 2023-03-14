#! /usr/bin/env python3

import paho.mqtt.client as mqtt
import logging as log
import json
import os
import sys

# Initiating logging
log.basicConfig(filename='cloud.log', filemode='a', level=log.INFO, format="[%(asctime)s] %(levelname)s %(message)s", datefmt='%d-%m-%Y %I:%M:%S %p')

AUTH_CLIENT_NAME = None
CLOUD_STORAGE_PATH = None

batchsize = -1
authenticated = 0

def on_message(client, userdata, message):
    global authenticated

    message = json.loads(message.payload.decode('UTF-8'))
    try:
        
        os.remove(f"{CLOUD_STORAGE_PATH}/{message['file']}")
        log.info(f"File Removed: {message['file']}")
    except:
        log.warning(f"File not Removed: {message['file']}")

    authenticated += 1
    if batchsize == authenticated:
        os.remove("signed_url.json")
        log.info(f"[{AUTH_CLIENT_NAME}]: Disconnecting...")
        client.disconnect()
        sys.exit(0)
    

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        log.info(f"[{AUTH_CLIENT_NAME}]: Connected!")
    else:
        log.warning(f"[{AUTH_CLIENT_NAME}]: Could not establish connection.")
        sys.exit(1)

def start_authetication(broker, port, interval, client_name, topic, qos, root_ca, device_cert, private_key, batch_size, cloud_storage_path):

    global AUTH_CLIENT_NAME
    global CLOUD_STORAGE_PATH
    global batchsize
    AUTH_CLIENT_NAME = client_name
    CLOUD_STORAGE_PATH = cloud_storage_path
    batchsize = batch_size

    AuthClient = mqtt.Client(client_name)

    AuthClient.tls_set(root_ca, device_cert, private_key)

    AuthClient.on_connect = on_connect
    AuthClient.on_message = on_message
    try:
        AuthClient.connect(broker, port, interval)
        AuthClient.subscribe(topic, qos)
    except Exception as e:
        log.INFO(f"Could not run Authentication client.")
        log.ERROR(e)
        sys.exit(1)

    AuthClient.loop_forever()