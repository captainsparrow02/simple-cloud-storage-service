#!/bin/env python3
import paho.mqtt.client as mqtt
import logging as log
import sys
import time

# Initiating logging
log.basicConfig(filename='cloud.log', filemode='a', level=log.INFO, format="[%(asctime)s] %(levelname)s %(message)s", datefmt='%d-%m-%Y %I:%M:%S %p')

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        log.info(f"[{CLIENT_NAME}]: Connected!")
    else:
        log.warning(f"[{CLIENT_NAME}]: Could not establish connection.")
        sys.exit(1)

def on_publish(client, userdata, message):
    log.info(f"[{CLIENT_NAME}]: Payload successfully published.")
    log.info(f"[{CLIENT_NAME}]: Disconnecting...")
    client.disconnect()
    sys.exit(0)

def start_publish(broker, port, interval, client_name, topic, qos, payload, root_ca, device_cert, private_key):
    time.sleep(2)

    global CLIENT_NAME
    CLIENT_NAME = client_name

    PublishClient = mqtt.Client(client_name)
    PublishClient.tls_set(root_ca, device_cert, private_key)

    PublishClient.on_connect = on_connect
    PublishClient.on_publish = on_publish
    
    try:
        PublishClient.connect(broker, port, interval)
        PublishClient.publish(topic, payload, qos)
    except Exception as e:
        log.info("Could not run publish client.")
        log.error(e)
        sys.exit(1)

    PublishClient.loop_forever()
