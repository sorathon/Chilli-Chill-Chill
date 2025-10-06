from flask import Flask, request
import threading, requests, io, base64, uuid, os
from PIL import Image

app = Flask(__name__)
CHANNEL_ACCESS_TOKEN = "BhgZemDVr0aBV4J6gNq3CQoTiz9XZWHP/0eJpoU233GBPqU89miapKTuj6jtNmPz5sXqj/4Idl8THLeDFbApngUPJcoc8fIEHMhmXRLkVCpAZs7H4zhoDPRX6BjuSgT7DJFD4XML0TRaZ3OH73OzYQdB04t89/1O/w1cDnyilFU="

# ✅ เก็บ message_id ที่เคยประมวลผลแล้ว
processed_ids = set()

def push_line_message(user_id, messages):
    headers = {
        "Authorization": f"Bearer {CHANNEL_ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    data = {"to": user_id, "messages": messages}
    resp = requests.post("https://api.line.me/v2/bot/message/push", headers=headers, json=data)
    if resp.status_code != 200:
        print("Push message failed:", resp.status_code, resp.text)

def get_line_image(message_id):
    headers = {"Authorization": f"Bearer {CHANNEL_ACCESS_TOKEN}"}
    url = f"https://api-data.line.me/v2/bot/message/{message_id}/content"
    resp = requests.get(url, headers=headers)
    return resp.content

def base64_to_image(base64_string):
    if "base64," in base64_string:
        base64_string = base64_string.split(",")[1]
    image_data = base64.b64decode(base64_string)
    return Image.open(io.BytesIO(image_data))

# ===== ฟังก์ชันประมวลผลใน background =====
def process_image_task(user_id, image_content):
    try:
        aws_url = "https://ai-chilli-service-520362133187.asia-southeast1.run.app/detect_count"
        files = {'image': ('image.jpg', io.BytesIO(image_content), 'image/jpeg')}
        res = requests.post(aws_url, files=files)

        if res.status_code == 200:
            response_data = res.json()
            counts = response_data.get("counts", {})
            image_base64 = response_data.get("image_base64")

            green_chili = counts.get("Thaichili_Green", 0)
            red_chili = counts.get("Thaichili_red", 0)
            reply_text = (
                f"🌶️ ผลการตรวจนับพริก:\n"
                f"• พริกสีเขียว: {green_chili} เม็ด\n"
                f"• พริกสีแดง: {red_chili} เม็ด"
            )

            messages = [{"type": "text", "text": reply_text}]

            if image_base64:
                image = base64_to_image(image_base64)
                filename = f"{uuid.uuid4()}.jpg"
                os.makedirs("static", exist_ok=True)
                save_path = os.path.join("static", filename)
                image.save(save_path)

                image_url = f"https://8a0b6a2dfad0.ngrok-free.app/static/{filename}"
                messages.append({
                    "type": "image",
                    "originalContentUrl": image_url,
                    "previewImageUrl": image_url
                })

            push_line_message(user_id, messages)
        else:
            push_line_message(user_id, [{"type": "text", "text": "เกิดข้อผิดพลาดจากโมเดล"}])

    except Exception as e:
        push_line_message(user_id, [{"type": "text", "text": f"Error: {e}"}])


# ===== Webhook =====
@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json
    for event in data.get("events", []):
        if event["type"] == "message" and event["message"]["type"] == "image":
            message_id = event["message"]["id"]
            user_id = event["source"]["userId"]

            # ✅ ถ้า message_id เคยเจอแล้ว → ข้ามเลย
            if message_id in processed_ids:
                print(f"🔁 ข้าม message_id ซ้ำ: {message_id}")
                return "OK", 200
            processed_ids.add(message_id)

            # ส่งข้อความแจ้งก่อน
            push_line_message(user_id, [{"type": "text", "text": "กำลังประมวลผลรูปของคุณ..."}])

            # โหลดรูปและประมวลผลแยก thread
            image_content = get_line_image(message_id)
            threading.Thread(target=process_image_task, args=(user_id, image_content)).start()

    return "OK", 200

if __name__ == "__main__":
    app.run(port=5000, debug=True)
