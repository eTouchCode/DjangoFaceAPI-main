import datetime
import requests
import time
from django.db import connection
import random
import string

def generate_random_id(length=15):
    characters = string.ascii_letters + string.digits
    random_id = ''.join(random.choice(characters) for i in range(length))
    return random_id

def post_detection_callback(company_callback_url, detection_data):
    try:
        print(detection_data)
        response = requests.post(company_callback_url, json=detection_data, verify=False)
        return response.status_code
    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}")
        return None

def validate_shift(company_id):
    with connection.cursor() as cursor:
        cursor.execute('SELECT name, start_time, end_time FROM api_workshift WHERE company_id = %s', (company_id,))
        rows = cursor.fetchall()
        
    if rows:
        shifts = []
        for row in rows:
            shift = {
                'shift_name': row[0],
                'start_time': row[1],
                'end_time': row[2]
            }
            shifts.append(shift)
        return shifts
    return None

def get_current_shift(shifts):
    current_time = datetime.datetime.now().time()
    
    for shift in shifts:
        start_time = datetime.datetime.strptime(shift['start_time'], '%H:%M:%S').time()
        end_time = datetime.datetime.strptime(shift['end_time'], '%H:%M:%S').time()
        
        if start_time <= current_time <= end_time:
            return shift['shift_name']
    return None

def handle_face_detection(company_id, detected_person, role, callback_url, camera_id):
    company_callback_url = callback_url
    detection_data = {
        'time': time.strftime('%Y-%m-%d %H:%M:%S'),
        'person': detected_person,
        'role': role
    }
    shifts = validate_shift(company_id)
    if shifts:
        current_shift_name = get_current_shift(shifts)
        if current_shift_name:
            detection_data['current_shift'] = current_shift_name
    cooldown_period = 3600  # Example cooldown period (1 hour)
    last_detection_time = get_last_detection_time(company_id, detected_person)
    if last_detection_time == 0 or time.time() - last_detection_time > cooldown_period:
        status_code = post_detection_callback(company_callback_url, detection_data)
        update_last_detection_time(company_id, detected_person, camera_id)

def get_last_detection_time(company_id, detected_person):
    with connection.cursor() as cursor:
        cursor.execute('''
            SELECT event_time 
            FROM api_cameraevent 
            JOIN api_companymember ON api_cameraevent.company_member = api_companymember.id
            WHERE api_companymember.company_id = %s AND api_companymember.name = %s
            ORDER BY event_time DESC
        ''', (company_id, detected_person))
        row = cursor.fetchone()
    return row[0].timestamp() if row else 0

def update_last_detection_time(company_id, detected_person, camera_id):
    with connection.cursor() as cursor:
        cursor.execute('SELECT id FROM api_companymember WHERE name = %s AND company_id = %s', (detected_person, company_id))
        member_row = cursor.fetchone()
        
    if member_row:
        member_id = member_row[0]
        with connection.cursor() as cursor:
            cursor.execute('''
                SELECT ce.event_time, ce.camera_id
                FROM api_cameraevent ce 
                JOIN api_companymember cm ON ce.company_member = cm.id 
                WHERE cm.id = %s
                ORDER BY ce.event_time DESC
            ''', (member_id,))
            last_event_time_row = cursor.fetchone()
        
        last_event_time = last_event_time_row[0] if last_event_time_row else 0

        with connection.cursor() as cursor:
            cursor.execute('''
                INSERT INTO api_cameraevent (company_member, event_time, camera_id) 
                VALUES (%s, %s, %s)
            ''', (member_id, datetime.datetime.now(), camera_id))
            print("Member Updated Successfully.")
            connection.commit()
    else:
        print(f"No member found with name '{detected_person}' in company {company_id}")

def add_camera2(nickname, ip, port, user, password, channel, enabled, company_id, company_hash, callback_url, rtsp_url, model_path, loc):
    generated_id = generate_random_id()  # Generate the random ID
    print("33333333333333333333333333333333333333333333333")
    with connection.cursor() as cursor:
        cursor.execute('''
            INSERT INTO api_camera (nickname, IP, port, `user`, password, channel, enabled, created_at, updated_at, company_id, generated_id)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ''', (nickname, ip, port, user, password, channel, enabled, datetime.datetime.now(), datetime.datetime.now(), company_id, generated_id))
        camera_id = cursor.lastrowid  # Get the ID of the last inserted row
        connection.commit()

    if enabled:
        from api.scheduler_utilities import start_camera_thread
        start_camera_thread(camera_id, company_id, company_hash, callback_url, rtsp_url, model_path, loc)
    
    return camera_id
