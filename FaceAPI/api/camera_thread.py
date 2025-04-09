
import time
import threading
import face_recognition
from collections import Counter
import cv2
import pickle
from api.camera_utilities import *


class CameraThread(threading.Thread):
    def __init__(self, camera_id, company_id, company_hash, callback_url, rtsp_url, model_path, loc):
        threading.Thread.__init__(self)
        self.camera_id = camera_id
        self.company_id = company_id
        self.company_hash = company_hash
        self.callback_url = callback_url
        self.DEFAULT_ENCODINGS_PATH = model_path
        self.BOUNDING_BOX_COLOR = "red"
        self.TEXT_COLOR = "Yellow"
        self.confidence_threshold = 2
        self.rtsp_url = rtsp_url
        self.loc = loc
        self.recently_detected = []
        self.last_cleared = time.time()
        self.running = True

    def stop(self):
        self.running = False

    def _recognize_face(self, unknown_encoding, loaded_encodings):
        boolean_matches = face_recognition.compare_faces(
            loaded_encodings["encodings"], unknown_encoding
        )
        votes = Counter(
            name
            for match, name in zip(boolean_matches, loaded_encodings["names"])
            if match
        )
        if votes:
            most_common = votes.most_common(1)[0]
            name, confidence = most_common[0], most_common[1]
            if confidence >= self.confidence_threshold:
                return name, confidence
            else:
                return "Unknown", 0
        else:
            return "Unknown", 0

    def recognize_faces(self, camera_id):
        try:
            # video_location = self.rtsp_url
            video_location = self.loc
            model = "hog"
            encodings_location = str(self.DEFAULT_ENCODINGS_PATH)
            
            with open(encodings_location, "rb") as f:
                loaded_encodings = pickle.load(f)

            video_capture = cv2.VideoCapture(video_location)
            if not video_capture.isOpened():
                print("Video not opened!")
            target_width = 1280 
            target_height = 720
            frame_skip = 0
            while self.running:
                ret, frame = video_capture.read()
                if not ret:
                    break

                frame_skip += 1
                if frame_skip % 10 != 0:
                    continue    
                print(frame_skip)
                frame = cv2.resize(frame, (target_width, target_height))
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                input_face_locations = face_recognition.face_locations(frame, model=model)
                input_face_encodings = face_recognition.face_encodings(
                    frame, input_face_locations
                )

                # pillow_image = Image.fromarray(frame)
                # draw = ImageDraw.Draw(pillow_image)

                for bounding_box, unknown_encoding in zip(
                    input_face_locations, input_face_encodings
                ):
                    name, confidence = self._recognize_face(unknown_encoding, loaded_encodings)
                    print(name)
                    print(confidence)
                    if confidence > 20:
                        print("########################################################")
                        print(f"Name: {name}")
                        role = "Super Admin"
                        now = time.time()
                        self.recently_detected = [
                            item for item in self.recently_detected if now - item['time'] <= 3600
                        ]
                        
                        # Clear the list every 2 hours
                        if now - self.last_cleared > 7200:
                            self.recently_detected = []
                            self.last_cleared = now
                            
                        if any(item['name'] == name and item['company_id'] == self.company_id for item in self.recently_detected):
                            print(f"{name} detected recently, skipping DB check.")
                        else:
                            handle_face_detection(self.company_id, name, role, self.callback_url, camera_id)
                            self.recently_detected.append({'name': name, 'company_id': self.company_id, 'time': now})
                #del draw
            print("Recognition completed successfully")
        except Exception as e:
            print(f"Error during face recognition: {str(e)}")

    def run(self):
        self.recognize_faces(self.camera_id)