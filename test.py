from sklearn.neighbors import KNeighborsClassifier
import cv2
import os
import csv
import time
from datetime import datetime

from db_utils import ensure_database, load_training_data, count_students

if os.name == "nt":
    from win32com.client import Dispatch
else:
    Dispatch = None


def speak(str1):
    if Dispatch is None:
        return
    speaker = Dispatch(("SAPI.SpVoice"))
    speaker.Speak(str1)


# --- 1. SETUP CAMERA & DETECTOR ---
video = cv2.VideoCapture(0)
facedetect = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")

# --- 2. LOAD DATA FROM SQLITE DATABASE ---
ensure_database()
FACES, LABELS = load_training_data()

if FACES.size == 0 or len(LABELS) == 0:
    print("No enrolled faces found. Run add_faces.py first.")
    video.release()
    raise SystemExit(1)

print(f"Shape of Faces matrix --> {FACES.shape}")
print(f"Count of face samples --> {len(LABELS)}")
print(f"Count of students --> {count_students()}")

# --- 3. TRAIN MODEL ---
knn = KNeighborsClassifier(n_neighbors=5)
knn.fit(FACES, LABELS)

COL_NAMES = ["NAME", "TIME"]
os.makedirs("Attendance", exist_ok=True)

while True:
    ret, frame = video.read()
    if not ret:
        print("Camera read failed.")
        break

    frame = cv2.flip(frame, 1)

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    faces = facedetect.detectMultiScale(gray, 1.3, 5)
    attendance = None
    attendance_file = None

    for (x, y, w, h) in faces:
        crop_img = frame[y : y + h, x : x + w, :]
        resized_img = cv2.resize(crop_img, (50, 50)).flatten().reshape(1, -1)
        output = knn.predict(resized_img)

        ts = time.time()
        date = datetime.fromtimestamp(ts).strftime("%d-%m-%Y")
        timestamp = datetime.fromtimestamp(ts).strftime("%H:%M-%S")
        attendance_file = "Attendance/Attendance_" + date + ".csv"

        cv2.rectangle(frame, (x, y), (x + w, y + h), (50, 50, 255), 2)
        cv2.rectangle(frame, (x, y - 40), (x + w, y), (50, 50, 255), -1)
        cv2.putText(frame, str(output[0]), (x, y - 15), cv2.FONT_HERSHEY_COMPLEX, 1, (255, 255, 255), 1)
        attendance = [str(output[0]), str(timestamp)]

    cv2.imshow("Frame", frame)

    k = cv2.waitKey(1)
    if k == ord("o"):
        if attendance is None or attendance_file is None:
            print("No face detected, attendance not recorded.")
            continue

        speak("Attendance Taken")
        time.sleep(1)

        file_exists = os.path.isfile(attendance_file)
        with open(attendance_file, "+a", newline="") as csvfile:
            writer = csv.writer(csvfile)
            if not file_exists:
                writer.writerow(COL_NAMES)
            writer.writerow(attendance)

    if k == ord("q"):
        break

video.release()
cv2.destroyAllWindows()
