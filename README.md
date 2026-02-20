# Face Recognition Attendance

This project now uses a **SQLite database** to store students and face samples.

## What changed
- You enroll a student face once using `add_faces.py`.
- The system remembers enrolled students in `data/face_attendance.db`.
- You can store **multiple students** and take attendance for all of them.
- If you try to enroll the same name again, the script asks whether to replace old samples.

## Run

### 1) Enroll student faces
```bash
python add_faces.py
```
- Enter student name.
- Let it capture 100 samples.
- Press `q` to cancel.

### 2) Take attendance
```bash
python test.py
```
- Press `o` to save attendance for detected face.
- Press `q` to quit.

Attendance CSV files are saved in `Attendance/`.
