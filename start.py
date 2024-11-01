
import cv2
from ultralytics import YOLO
import numpy as np
import time
from googletrans import Translator
import threading
import speech_recognition as sr
import queue
import atexit
from gtts import gTTS
import playsound
import os

# YOLO 모델 로드 및 설정
model_path = "yolo_models/yolov10x.pt"
model = YOLO(model_path)
class_names = model.names
cap = cv2.VideoCapture(0)
focal_length = 295
known_height = 1.5

def compute_distance(object_height_in_image):
    if object_height_in_image > 0:
        return (known_height * focal_length) / object_height_in_image
    return float('inf')

# AsyncSpeechEngine 클래스 정의
class AsyncSpeechEngine:
    def __init__(self):
        self.queue = queue.Queue()
        self.thread = threading.Thread(target=self._process_queue, daemon=True)
        self.thread.start()

    def _process_queue(self):
        while True:
            message = self.queue.get()
            if message is None:  # 종료 신호
                break
            self._speak(message)

    def _speak(self, message):
        try:
            tts = gTTS(message, lang='ko')
            filename = 'temp.mp3'
            tts.save(filename)
            playsound.playsound(filename)
            os.remove(filename)
        except Exception as e:
            print(f"Speech error: {e}")

    def speak(self, message):
        self.queue.put(message)

    def close(self):
        self.queue.put(None)  # 종료 신호
        self.thread.join()

# 음성 엔진 초기화
speech_engine = AsyncSpeechEngine()
atexit.register(speech_engine.close)

translator = Translator()

def translate_label(label):
    try:
        translated = translator.translate(label, src='en', dest='ko')
        return translated.text
    except Exception as e:
        print(f"Translation error: {e}")
        return label

def speak_warning(label, distance):
    translated_label = translate_label(label)
    message = f"{translated_label}가 {distance:.2f}미터 거리에 있습니다. 주의하세요."
    speech_engine.speak(message)

def speak_closest_object(label, distance):
    translated_label = translate_label(label)
    message = f"가장 가까운 객체는 {translated_label}입니다. 거리: {distance:.2f}미터입니다."
    speech_engine.speak(message)

def voice_recognition_thread():
    recognizer = sr.Recognizer()
    mic = sr.Microphone()
    last_command_time = 0
    command_interval =10  # 명령을 인식한 후 다시 인식하기 전 대기 시간 (초)

    # 유사 명령어 리스트
    command_variants = ["앞에 뭐","앞에 뭐가","앞에","앞","앞에 뭐가 있", "앞에 뭐가 있어", "앞에 뭐 있어", "아페 뭐가 있어"]

    while True:
        with mic as source:
            print("Listening for command...")
            try:
                audio = recognizer.listen(source, timeout=2, phrase_time_limit=2)
                command = recognizer.recognize_google(audio, language='ko-KR')
                print(f"You said: {command}")
                current_time = time.time()
                # 유사 명령어 매칭
                if any(variant in command for variant in command_variants) and (current_time - last_command_time) >= command_interval:
                    if top_3:
                        closest_object_label = top_3[0][2]
                        closest_object_distance = top_3[0][0]
                        speak_closest_object(closest_object_label, closest_object_distance)
                    last_command_time = current_time
            except sr.UnknownValueError:
                print("Sorry, I did not understand the audio.")
            except sr.RequestError as e:
                print(f"Could not request results; {e}")
            except sr.WaitTimeoutError:
                print("Listening timed out while waiting for phrase to start.")

# 음성 인식 스레드 시작
voice_thread = threading.Thread(target=voice_recognition_thread, daemon=True)
voice_thread.start()

num_classes = len(class_names)
class_colors = [tuple(int(x * 255) for x in np.random.rand(3)) for _ in range(num_classes)]
class_color_map = {i: class_colors[i] for i in range(num_classes)}

last_warning_time = 0
warning_interval = 12 # 거리 측정 경고 딜레이
last_distance = None
distance_change_threshold = 0.2

while True:
    ret, frame = cap.read()
    if not ret:
        break

    results = model(frame)
    annotated_frame = frame.copy()
    distances = []

    for result in results[0].boxes:
        scores = result.conf.cpu().numpy()
        coords = result.xyxy.cpu().numpy()
        class_ids = result.cls.cpu().numpy()

        for i, score in enumerate(scores):
            if score >= 0.4:
                x1, y1, x2, y2 = map(int, coords[i])
                class_id = int(class_ids[i])
                label = class_names[class_id]
                object_height_in_image = y2 - y1
                distance = compute_distance(object_height_in_image)
                distances.append((distance, (x1, y1, x2, y2), label, class_id))

    distances.sort(key=lambda x: x[0])
    top_3 = distances[:3]

    print("All detected objects:")
    for distance, (x1, y1, x2, y2), label, class_id in distances:
        print(f"Distance: {distance:.2f}m, Coordinates: ({x1}, {y1}, {x2}, {y2}), Label: {label}")

    print("\nTop 3 closest objects:")
    for idx, (distance, (x1, y1, x2, y2), label, class_id) in enumerate(top_3):
        print(f"Rank {idx+1}: Distance: {distance:.2f}m, Coordinates: ({x1}, {y1}, {x2}, {y2}), Label: {label}")

    if top_3 and top_3[0][0] <= 1.2:
        current_time = time.time()
        if (current_time - last_warning_time) >= warning_interval:
            if last_distance is None or abs(last_distance - top_3[0][0]) >= distance_change_threshold:
                closest_object_label = top_3[0][2]
                closest_object_distance = top_3[0][0]
                speak_warning(closest_object_label, closest_object_distance)
                last_warning_time = current_time
                last_distance = closest_object_distance
    else:
        last_distance = None

    for idx, (distance, (x1, y1, x2, y2), label, class_id) in enumerate(top_3):
        color = class_color_map[class_id]
        cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), color, 2)
        cv2.putText(annotated_frame, f"{idx+1}: {label}", (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
        distance_label = f"Distance: {distance:.2f}m"
        cv2.putText(annotated_frame, distance_label, (x1, y2 + 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

    cv2.imshow('YOLO Object Detection', annotated_frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
