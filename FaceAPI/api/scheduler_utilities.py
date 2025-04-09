from apscheduler.schedulers.background import BackgroundScheduler
from api.camera_thread import CameraThread
from django.db import connection

scheduler = BackgroundScheduler()
scheduler.start()

camera_threads = {}

def start_camera_thread(camera_id, company_id, company_hash, callback_url, rtsp_url, model_path, loc):
    camera_thread = CameraThread(camera_id, company_id, company_hash, callback_url, rtsp_url, model_path, loc)
    camera_threads[camera_id] = camera_thread
    camera_thread.start()
    print(f"Camera thread {camera_id} started.")

def stop_camera_thread(camera_id):
    if camera_id in camera_threads:
        camera_threads[camera_id].stop()
        camera_threads[camera_id].join()
        del camera_threads[camera_id]
        print(f"Camera thread {camera_id} stopped.")

def stop_all_camera_threads():
    with connection.cursor() as cursor:
        cursor.execute("SELECT id FROM api_camera")
        camera_ids = cursor.fetchall()
        for (camera_id,) in camera_ids:
            stop_camera_thread(camera_id)

def start_all_camera_threads():
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT cam.id, cam.company_id, com.company_hash, com.callback_url,
                   cam.nickname, cam.IP, cam.port, cam.user, cam.password, cam.channel, cam.enabled
            FROM api_company com 
            INNER JOIN api_camera cam ON com.id = cam.company_id
            WHERE cam.enabled = 1
        """)
        cameras = cursor.fetchall()

    for camera in cameras:
        camera_id, company_id, company_hash, callback_url, nickname, ip, port, user, password, channel, enabled = camera
        rtsp_url = f"rtsp://{user}:{password}@{ip}:{port}/live/{channel}"
        print(rtsp_url)
        model_path = f"./output/{company_hash}.pkl"
        print(model_path)
        loc = "D:\\Work_Yousuf_New\\py\\2024\\June\\FaceAppProject\\API\\videos\\33.mp4"
        start_camera_thread(camera_id, company_id, company_hash, callback_url, rtsp_url, model_path, loc)

def schedule_camera_management():
    # Stop all camera threads at 11:30 PM every day
    scheduler.add_job(stop_all_camera_threads, 'cron', hour=23, minute=30)

    # Start all camera threads at 11:35 PM every day
    scheduler.add_job(start_all_camera_threads, 'cron', hour=23, minute=35)
