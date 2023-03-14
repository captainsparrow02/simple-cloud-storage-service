#! /usr/bin/env python3

import paho.mqtt.client as mqtt
import json
import os
import sys
import time
import threading
import logging as log
from publish import start_publish
from subscribe import start_subscribe
from upload import upload_file
from authenticate import start_authetication

# log.basicConfig(filename='/var/tmp/cloud.log', filemode='w', level=log.INFO, format='[%(asctime)s]- %(message)s', datefmt='%d-%m-%Y %I:%M:%S %p')
# Initiating logging
log.basicConfig(filename='cloud.log', filemode='w', level=log.INFO, format="[%(asctime)s] %(levelname)s %(message)s", datefmt='%d-%m-%Y %I:%M:%S %p')

# Reading configuration file
with open('cloud.conf','r') as config:
    data = json.load(config)

# AWS Setup
BROKER = data['CLOUD']['ARN']
PORT = int(data['CLOUD']['PORT'])
MQTT_INTERVAL = int(data['CLOUD']['MQTT_INTERVAL'])
BUCKET_NAME = data['CLOUD']['BUCKET_NAME']

# Publish Client Setuo
PUBLISH_CLIENT_NAME = data['CLOUD']['PUBLISH']['CLIENT_NAME']
PUBLISH_TOPIC = data['CLOUD']['PUBLISH']['TOPIC']
PUBLISH_QoS = int(data['CLOUD']['PUBLISH']['QoS'])

# Subscribe Client Setuo
SUBSCRIBE_CLIENT_NAME = data['CLOUD']['SUBSCRIBE']['CLIENT_NAME']
SUBSCRIBE_TOPIC = data['CLOUD']['SUBSCRIBE']['TOPIC']
SUBSCRIBE_QoS = int(data['CLOUD']['SUBSCRIBE']['QoS'])

# Authenticate Client Setuo
AUTHENTICATE_CLIENT_NAME = data['CLOUD']['AUTHENTICATE']['CLIENT_NAME']
AUTHENTICATE_TOPIC = data['CLOUD']['AUTHENTICATE']['TOPIC']
AUTHENTICATE_QoS = int(data['CLOUD']['AUTHENTICATE']['QoS'])

# Certificate Path
ROOT_CA = data['CLOUD']['ROOT_CA_PATH']
DEVICE_CERT = data['CLOUD']['DEVICE_CERT_PATH']
PRIVATE_KEY = data['CLOUD']['PRIVATE_KEY_PATH']

# Local Setup
CLOUD_STORAGE_PATH = data['LOCAL']['STORAGE_PATH']

def signed_url_exist():
	tries = 0
	while "signed_url.json" not in os.listdir():
		if tries == 5:
			log.warning("Could not recieve Signed URLs")
			sys.exit(1)
		tries += 1
		time.sleep(2)
	log.info("Signed URLs recieved.")
	return True

def upload_manager(files):
	
	batch_size = len(files)

	payload = json.dumps({
		'bucket_name' : BUCKET_NAME,
		'files' : files
		})

	susbcribe_thread = threading.Thread(target = start_subscribe, args = [
		BROKER,
		PORT,
		MQTT_INTERVAL,
		SUBSCRIBE_CLIENT_NAME,
		SUBSCRIBE_TOPIC,
		SUBSCRIBE_QoS,
		ROOT_CA,
		DEVICE_CERT,
		PRIVATE_KEY
		])

	publish_thread = threading.Thread(target = start_publish, args = [
		BROKER,
		PORT,
		MQTT_INTERVAL,
		PUBLISH_CLIENT_NAME,
		PUBLISH_TOPIC,
		PUBLISH_QoS,
		payload,
		ROOT_CA,
		DEVICE_CERT,
		PRIVATE_KEY
		])

	susbcribe_thread.start()
	publish_thread.start()
	susbcribe_thread.join()
	publish_thread.join()

	if signed_url_exist():

		upload_thread = threading.Thread(target = upload_file, args = [
			CLOUD_STORAGE_PATH
		])
		authentication_thread = threading.Thread(target= start_authetication, args=[
			BROKER,
			PORT,
			MQTT_INTERVAL,
			AUTHENTICATE_CLIENT_NAME,
			AUTHENTICATE_TOPIC,
			AUTHENTICATE_QoS,
			ROOT_CA,
			DEVICE_CERT,
			PRIVATE_KEY,
			batch_size,
			CLOUD_STORAGE_PATH
			
		])
		upload_thread.start()
		authentication_thread.start()
		upload_thread.join()
		authentication_thread.join()

def main():
	log.info("Cloud Storage app started running.")
	while True:
		if len(os.listdir(CLOUD_STORAGE_PATH)):
			log.info("Files found! Starting upload manager.")
			upload_manager(os.listdir(CLOUD_STORAGE_PATH)[:10])
		time.sleep(5)
main()
