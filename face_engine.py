import os
import pickle
import cv2
import numpy as np
import face_recognition

BASE_DIR = os.path.dirname(__file__)
FACES_DIR = os.path.join(BASE_DIR, "known_faces")
ENC_FILE = os.path.join(BASE_DIR, "known_faces.pkl")

_known_encodings = []
_known_names = []
_loaded = False


def load_known_faces():
    global _known_encodings, _known_names, _loaded
    if _loaded:
        return

    if os.path.exists(ENC_FILE):
        with open(ENC_FILE, "rb") as f:
            data = pickle.load(f)
        _known_encodings = data["encodings"]
        _known_names = data["names"]
        _loaded = True
        return

    _known_encodings = []
    _known_names = []

    for person in os.listdir(FACES_DIR):
        pdir = os.path.join(FACES_DIR, person)
        if not os.path.isdir(pdir):
            continue

        for imgf in os.listdir(pdir):
            if not imgf.lower().endswith((".jpg", ".png", ".jpeg")):
                continue
            img = cv2.imread(os.path.join(pdir, imgf))
            if img is None:
                continue

            rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            encs = face_recognition.face_encodings(rgb)
            for e in encs:
                _known_encodings.append(e)
                _known_names.append(person)

    with open(ENC_FILE, "wb") as f:
        pickle.dump(
            {"encodings": _known_encodings, "names": _known_names}, f
        )

    _loaded = True


def recognize_faces(frame, tolerance=0.55):
    load_known_faces()

    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    locs = face_recognition.face_locations(rgb, model="hog")
    encs = face_recognition.face_encodings(rgb, locs)

    names = []

    for enc in encs:
        if not _known_encodings:
            names.append("Unknown")
            continue

        dists = face_recognition.face_distance(_known_encodings, enc)
        idx = int(np.argmin(dists))
        if dists[idx] <= tolerance:
            names.append(_known_names[idx])
        else:
            names.append("Unknown")

    return names
