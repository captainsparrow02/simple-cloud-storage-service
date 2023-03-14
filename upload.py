#! /usr/bin/env python3

import requests
import json
import logging as log

# Initiating logging
log.basicConfig(filename='cloud.log', filemode='a', level=log.INFO, format="[%(asctime)s] %(levelname)s %(message)s", datefmt='%d-%m-%Y %I:%M:%S %p')

def upload_file(path):

	log.info("Upload started.")
	with open('signed_url.json','r') as f:
		payload = json.loads(f.read())
		f.close()

	for data in payload['payload']:
		file, url = data['data']['fields']['key'], data['data']['url']
		with open(f'{path}/{file}', 'rb') as f:
			file_data = {'file':(file, f)}
			try:
				response = requests.post(url, data=data['data']['fields'], files = file_data)
				log.info(f"{file} uploaded. Response code {response.status_code}")
			except Exception as e:
				log.info(f"{file} could not be uploaded.")
				log.error(e)
