import os
import threading
import requests
from flask import Flask, request, jsonify

BOT_TOKEN = os.environ.get("BOT_TOKEN", "").strip()
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()
RENDER_EXTERNAL_URL = os.environ.get("RENDER_EXTERNAL_URL", "").strip().rstrip("/")
WEBHOOK_SECRET = os.environ.get("WEBHOOK_SECRET", "").strip()

app = Flask(__name__)
TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}"

def telegram_send(chat_id, text):
    if not BOT_TOKEN:
        return
    requests.post(
        f"{TELEGRAM_API}/sendMessage",
        json={"chat_id": chat_id, "text": text[:4000]},
        timeout=20,
    ).raise_for_status()

def ask_gemini(user_text):
    if not GEMINI_API_KEY:
        return "الذكاء الاصطناعي مازال ما تبرمجش. خاص المالك يزيد GEMINI_API_KEY فإعدادات الاستضافة."
    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        "gemini-2.5-flash:generateContent?key=" + GEMINI_API_KEY
    )
    payload = {
        "system_instruction": {
            "parts": [{
                "text": "أنت rabi3_ff_bot، مساعد ودود يتكلم بالدارجة المغربية أو بلغة المستخدم. "
                        "أجب باختصار ووضوح. لا تدّع أنك تستطيع شحن جواهر Free Fire أو اختراق اللعبة."
            }]
        },
        "contents": [{"parts": [{"text": user_text[:5000]}]}],
        "generationConfig": {"temperature": 0.7, "maxOutputTokens": 700},
    }
    response = requests.post(url, json=payload, timeout=45)
    if response.status_code >= 400:
        return "سمح ليا، خدمة الذكاء الاصطناعي ما جاوباتش دابا. جرّب من بعد."
    data = response.json()
    try:
        return data["candidates"][0]["content"]["parts"][0]["text"].strip()
    except (KeyError, IndexError, TypeError):
        return "ما قدرتش نوجد جواب دابا. عاود جرّب من فضلك."

@app.get("/")
def home():
    return "rabi3_ff_bot is running", 200

@app.post("/telegram-webhook")
def telegram_webhook():
    if WEBHOOK_SECRET:
        supplied = request.headers.get("X-Telegram-Bot-Api-Secret-Token", "")
        if supplied != WEBHOOK_SECRET:
            return jsonify({"ok": False}), 403

    update = request.get_json(silent=True) or {}
    message = update.get("message") or update.get("edited_message")
    if not message or not message.get("chat"):
        return jsonify({"ok": True})

    chat_id = message["chat"]["id"]
    text = (message.get("text") or "").strip()
    if not text:
        telegram_send(chat_id, "كنفهم الرسائل المكتوبة دابا. صيفط ليا سؤال بالكتابة 😊")
        return jsonify({"ok": True})

    if text.startswith("/start"):
        telegram_send(chat_id, "سلام! 🤖 أنا rabi3_ff_bot، مساعدك بالذكاء الاصطناعي. كتب ليا أي سؤال ونحاول نعاونك.")
        return jsonify({"ok": True})

    if text.startswith("/help"):
        telegram_send(chat_id, "كتب ليا أي سؤال باش نجاوبك بالذكاء الاصطناعي. استعمل /start للبداية.")
        return jsonify({"ok": True})

    try:
        reply = ask_gemini(text)
        telegram_send(chat_id, reply or "ما لقيتش جواب مناسب، جرّب تسولني بطريقة أخرى.")
    except Exception:
        # Avoid exposing credentials or server errors to Telegram users.
        telegram_send(chat_id, "وقع مشكل تقني بسيط. جرّب من بعد.")
    return jsonify({"ok": True})

def configure_webhook():
    if not (BOT_TOKEN and RENDER_EXTERNAL_URL):
        print("Set BOT_TOKEN and RENDER_EXTERNAL_URL to enable Telegram webhook.")
        return
    payload = {"url": f"{RENDER_EXTERNAL_URL}/telegram-webhook"}
    if WEBHOOK_SECRET:
        payload["secret_token"] = WEBHOOK_SECRET
    try:
        r = requests.post(f"{TELEGRAM_API}/setWebhook", json=payload, timeout=20)
        print("Telegram webhook setup:", r.status_code, r.text[:300])
    except Exception as e:
        print("Webhook setup failed:", type(e).__name__)

if os.environ.get("BOT_TOKEN") and os.environ.get("RENDER_EXTERNAL_URL"):
    threading.Thread(target=configure_webhook, daemon=True).start()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", "10000"))
    app.run(host="0.0.0.0", port=port)
