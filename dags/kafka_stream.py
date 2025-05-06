import uuid
from datetime import datetime
from airflow import DAG # Airflow dag for workflow scheduling
from airflow.operators.python import PythonOperator # To run python functions as tasks

default_args = {
    'owner': 'Hamza',
    'start_date': datetime(2025, 5, 5, 10, 00) 
}

# Function to get the data from random user api 
def get_data():
    import requests

    res = requests.get("https://randomuser.me/api/")
    res = res.json()
    res = res['results'][0]

    return res

# function to reformat and clean the api response
def format_data(res):
    data = {}
    location = res['location']

    data['id'] = uuid.uuid4() # Generate a unique ID
    data['first_name'] = res['name']['first']
    data['last_name'] = res['name']['last']
    data['gender'] = res['gender']
    data['address'] = f"{str(location['street']['number'])} {location['street']['name']}, " \
                      f"{location['city']}, {location['state']}, {location['country']}"
    data['post_code'] = location['postcode']
    data['email'] = res['email']
    data['username'] = res['login']['username']
    data['dob'] = res['dob']['date']
    data['registered_date'] = res['registered']['date']
    data['phone'] = res['phone']
    data['picture'] = res['picture']['medium']

    return data

# Function to continuously stream data to kafka for 60s
def stream_data():
    import json
    from kafka import KafkaProducer
    import time # For handling timing
    import logging # For handling errors

    # Create producer to send messages to the topic & Connect to the Kafka broker (running inside Docker, port 29092), 5s wait
    producer = KafkaProducer(bootstrap_servers=['broker:29092'], max_block_ms=5000)
    
    curr_time = time.time() # Record current timeStamp

    while True: 
        if time.time() > curr_time + 60: #1 minute
            break 
        try:
            res = get_data() # fetch raw data
            res = format_data(res) # Transform it 
            
            #Send the data as json-encoded string to 'users_created' topic
            producer.send('users_created', json.dumps(res).encode('utf-8'))
        except Exception as e:
            logging.error(f'An error occured: {e}')
            continue

with DAG('user_automation',
         default_args=default_args,
         schedule_interval='@daily',
         catchup=False) as dag:
    # Define the task that will run the stream_data() function 
    streaming_task = PythonOperator(
        task_id='stream_data_from_api', # Name of the task
        python_callable=stream_data
    )
