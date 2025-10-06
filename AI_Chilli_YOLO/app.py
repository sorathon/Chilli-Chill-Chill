from flask import Flask, request, jsonify
from ultralytics import YOLO
import numpy as np
from PIL import Image
import cv2
import base64
from pymongo import MongoClient
from datetime import datetime
import os
import certifi

app = Flask(__name__)
THRESHOLD = 0.7

# Model Configuration
MODEL_PATH = "best.pt"
if not os.path.exists(MODEL_PATH):
    print(f"Error: Model file not found at {MODEL_PATH}")
model = YOLO(MODEL_PATH)


MONGO_URI = "mongodb+srv://sorathonaof2548_db_user:acCgla1TnVfBed4j@cluster0.z8ld0ke.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
MONGO_DB_NAME = "chilli_detection_db"
MONGO_COLLECTION_NAME = "detection_logs"

#connection to the database
try:
    ca = certifi.where()
    client = MongoClient(MONGO_URI, tlsCAFile=ca)
    db = client[MONGO_DB_NAME]
    collection = db[MONGO_COLLECTION_NAME]
    client.admin.command('ismaster')
    print("✅ MongoDB connection successful.")
except Exception as e:
    print(f"❌ Could not connect to MongoDB: {e}")
    client = None
    collection = None


#Class
TARGET_CLASSES = ["Thaichili_Green", "Thaichili_red"]
COLORS = {"Thaichili_Green": (0, 255, 0), "Thaichili_red": (0, 0, 255)}

class_names = model.model.names

def read_image_from_request(file):
    """Reads an image from a Flask file upload and converts it for OpenCV."""
    img = Image.open(file.stream).convert("RGB")
    img_np = np.array(img)
    return cv2.cvtColor(img_np, cv2.COLOR_RGB2BGR)


@app.route("/detect_count", methods=["POST"])
def detect_count():
    if "image" not in request.files:
        return jsonify({"error": "No image part in the request"}), 400
    
    file = request.files["image"]
    
    if file.filename == '':
        return jsonify({"error": "No image selected for uploading"}), 400

    img = read_image_from_request(file)
    
    # Run prediction
    results = model.predict(img, conf=THRESHOLD, verbose=False)

    target_ids = {}
    for target in TARGET_CLASSES:
        if target not in class_names.values():
            return jsonify({"error": f"Class '{target}' not found in the model"}), 400
        target_ids[target] = [k for k, v in class_names.items() if v == target][0]

    counts = {cls: 0 for cls in TARGET_CLASSES}
    detected_objects = []

    for r in results:
        for box in r.boxes:
            cls_id = int(box.cls)
            class_name_detected = class_names.get(cls_id)
            
            if class_name_detected in TARGET_CLASSES:
                counts[class_name_detected] += 1
                
                x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
                confidence = float(box.conf)
                
                detected_objects.append({
                    "class_name": class_name_detected,
                    "confidence": round(confidence, 4),
                    "bounding_box": {"x1": x1, "y1": y1, "x2": x2, "y2": y2}
                })
                
                label = f"{class_name_detected} {confidence:.2f}"
                color = COLORS[class_name_detected]
                cv2.rectangle(img, (x1, y1), (x2, y2), color, 2)
                cv2.putText(img, label, (x1, y1 - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

    _, buffer = cv2.imencode(".jpg", img)
    img_as_text = base64.b64encode(buffer).decode("utf-8")

    # Save to MongoDB
    if collection is not None:
        try:
            log_document = {
                "filename": file.filename,
                "timestamp": datetime.utcnow(),
                "total_counts": counts,
                "detected_objects": detected_objects,
                "image_base64": img_as_text,
            }
            collection.insert_one(log_document)
            print(f"✅ Successfully saved detection log for '{file.filename}' to MongoDB.")
        except Exception as e:
            print(f"❌ Error saving to MongoDB: {e}")
            return jsonify({"error": "Could not save log to database"}), 500

    return jsonify({
        "counts": counts,
        "image_base64": img_as_text
    })


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
