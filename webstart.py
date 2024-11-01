from flask import Flask, render_template, Response, jsonify 
import cv2
from ultralytics import YOLO
import numpy as np
import threading #여러 개의 스레드를 실행할 때 좋음 ㅋ
import time
from googletrans import Translator #Google 번역 API를 사용하는 파이썬 라이브러리로, 텍스트를 여러 언어로 번역하는 거임
import queue # 데이터 전달
import atexit # 모듈은 프로그램이 정상 종료되기 직전에 특정 함수를 호출
from gtts import gTTS
import playsound
import os
import speech_recognition as sr
import webbrowser


app = Flask(__name__)

# YOLO 모델 로드 및 설정
model_path = "yolo_models/yolo11x.pt"
model = YOLO(model_path)
class_names = model.names
focal_length = 295
known_height = 1.5
cap = cv2.VideoCapture(0)

# 객체 인식 실행 여부를 제어하는 플래그 변수
is_running = False
is_voice_active = False  # 음성 인식 활성화 여부 플래그

# 색상 생성
num_classes = len(class_names)
class_colors = [tuple(int(x * 255) for x in np.random.rand(3)) for _ in range(num_classes)]
class_color_map = {i: class_colors[i] for i in range(num_classes)}

# 거리 계산 함수
def compute_distance(object_height_in_image):
    if object_height_in_image > 0:
        return (known_height * focal_length) / object_height_in_image
    return float('inf')

# AsyncSpeechEngine 클래스 정의 (음성 엔진)
class AsyncSpeechEngine:
    def __init__(self):
        self.queue = queue.Queue()
        self.thread = threading.Thread(target=self._process_queue, daemon=True)
        self.thread.start()

    def _process_queue(self):
        while True:
            message = self.queue.get()
            if message is None:
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
        self.queue.put(None)
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
    command_interval = 10  # 명령을 인식한 후 다시 인식하기 전 대기 시간 (초)

    command_variants = ["앞에 뭐", "앞에 뭐가", "앞에", "앞", "앞에 뭐가 있", "앞에 뭐가 있어", "앞에 뭐 있어", "아페 뭐가 있어"]

    global top_5
    while True:
        if not is_voice_active:  # 음성 인식이 비활성화된 경우 계속 대기
            time.sleep(0.1)
            continue
        
        with mic as source:
            print("Listening for command...")
            try:
                audio = recognizer.listen(source, timeout=2, phrase_time_limit=2)
                command = recognizer.recognize_google(audio, language='ko-KR')
                print(f"You said: {command}")
                current_time = time.time()

                if any(variant in command for variant in command_variants) and (current_time - last_command_time) >= command_interval:
                    if top_5:
                        closest_object_label = top_5[0][2]
                        closest_object_distance = top_5[0][0]
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

# 웹캠 프레임을 브라우저로 스트리밍하는 함수
def generate_frames():
    global top_5
    last_warning_time = 0
    warning_interval = 12  # 거리 측정 경고 딜레이
    last_distance = None
    distance_change_threshold = 0.2

    while True:
        if not is_running:  # 객체 인식이 비활성화된 경우 계속 대기
            time.sleep(0.1)
            continue

        success, frame = cap.read()
        if not success:
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

                    # 모든 감지된 객체에 대해 박스와 라벨 표시
                    color = class_color_map[class_id]
                    cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), color, 2)
                    label_text = f"{label}: {distance:.2f}m"
                    cv2.putText(annotated_frame, label_text, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

        distances.sort(key=lambda x: x[0])
        top_5 = distances[:5]

        if top_5 and top_5[0][0] <= 1.2:
            current_time = time.time()
            if (current_time - last_warning_time) >= warning_interval:
                if last_distance is None or abs(last_distance - top_5[0][0]) >= distance_change_threshold:
                    closest_object_label = top_5[0][2]
                    closest_object_distance = top_5[0][0]
                    speak_warning(closest_object_label, closest_object_distance)
                    last_warning_time = current_time
                    last_distance = closest_object_distance
        else:
            last_distance = None

        ret, buffer = cv2.imencode('.jpg', annotated_frame)
        frame = buffer.tobytes()

        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

@app.route('/start_detection', methods=['POST'])
def start_detection():
    global is_running
    is_running = True
    return jsonify({"status": "started"})

@app.route('/stop_detection', methods=['POST'])
def stop_detection():
    global is_running
    is_running = False
    return jsonify({"status": "stopped"})

@app.route('/start_voice', methods=['POST'])
def start_voice():
    global is_voice_active
    is_voice_active = True
    return jsonify({"status": "voice started"})

@app.route('/stop_voice', methods=['POST'])
def stop_voice():
    global is_voice_active
    is_voice_active = False
    return jsonify({"status": "voice stopped"})

@app.route('/get_top_objects')
def get_top_objects():
    global top_5
    top_objects = []
    for idx, (distance, _, label, _) in enumerate(top_5):
        top_objects.append({
            "label": label,
            "distance": f"{distance:.2f}"
        })

    while len(top_objects) < 5:
        top_objects.append({"label": "없음", "distance": "0.00"})

    return jsonify(top_objects)

@app.route('/')
def index():
    return render_template('webtest.html')

@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == "__main__":
    # Start the Flask server in a separate thread
    from threading import Thread
    def run_flask():
        app.run(host='0.0.0.0', port=5000)
    
    flask_thread = Thread(target=run_flask)
    flask_thread.start()
    
    # Open the web browser
    webbrowser.open('http://127.0.0.1:5000')