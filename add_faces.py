import cv2
import numpy as np

from db_utils import ensure_database, student_exists, upsert_student_samples

SAMPLES_PER_STUDENT = 100


def main() -> None:
    ensure_database()

    video = cv2.VideoCapture(0)
    face_cascade = cv2.CascadeClassifier(
        cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
    )
    faces_data = []
    frame_count = 0

    name = input("Enter student name: ").strip()
    if not name:
        print("Name cannot be empty.")
        return

    replace_existing = False
    if student_exists(name):
        choice = input(
            f"'{name}' already exists. Replace existing face samples? (y/n): "
        ).strip().lower()
        if choice != "y":
            print("Enrollment cancelled. Existing data kept.")
            return
        replace_existing = True

    print("Look at the camera. Press 'q' to cancel enrollment.")

    while True:
        ret, frame = video.read()
        if not ret:
            print("Camera read failed. Please check webcam.")
            break

        frame = cv2.flip(frame, 1)
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, 1.3, 5)

        for (x, y, w, h) in faces:
            crop_img = frame[y : y + h, x : x + w, :]
            resized_img = cv2.resize(crop_img, (50, 50))
            if len(faces_data) < SAMPLES_PER_STUDENT and frame_count % 10 == 0:
                faces_data.append(resized_img)
            frame_count += 1

            cv2.putText(
                frame,
                f"Samples: {len(faces_data)}/{SAMPLES_PER_STUDENT}",
                (20, 40),
                cv2.FONT_HERSHEY_COMPLEX,
                0.8,
                (50, 50, 255),
                2,
            )
            cv2.rectangle(frame, (x, y), (x + w, y + h), (50, 50, 255), 1)

        cv2.imshow("Face Enrollment", frame)
        k = cv2.waitKey(1)
        if k == ord("q") or len(faces_data) == SAMPLES_PER_STUDENT:
            break

    video.release()
    cv2.destroyAllWindows()

    if len(faces_data) != SAMPLES_PER_STUDENT:
        print("Enrollment incomplete. No data saved.")
        return

    faces_array = np.asarray(faces_data, dtype=np.float32).reshape(SAMPLES_PER_STUDENT, -1)
    upsert_student_samples(name, faces_array, replace_existing=replace_existing)
    print(f"Saved {SAMPLES_PER_STUDENT} samples for {name}.")


if __name__ == "__main__":
    main()
