import os, io, wave, re, traceback, asyncio
import numpy as np
import sherpa_onnx
import edge_tts
from flask import Flask, request, send_file, jsonify, make_response
from flask_cors import CORS
from waitress import serve

app = Flask(__name__)
CORS(app)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# --- 1. إعداد المحرك المحلي ---
def create_tts_engine(folder_name, model_prefix):
    folder_path = os.path.join(BASE_DIR, folder_name)
    model_path = os.path.join(folder_path, f"{model_prefix}.onnx")
    tokens_path = os.path.join(folder_path, "tokens.txt")
    data_dir = os.path.join(BASE_DIR, "espeak-ng-data")
    if not os.path.exists(model_path): return None
    try:
        config = sherpa_onnx.OfflineTtsConfig(
            model=sherpa_onnx.OfflineTtsModelConfig(
                vits=sherpa_onnx.OfflineTtsVitsModelConfig(
                    model=model_path, tokens=tokens_path, data_dir=data_dir, lexicon=""
                ),
                num_threads=2,
            )
        )
        return sherpa_onnx.OfflineTts(config)
    except: return None

local_voices = {
    "kareem": create_tts_engine(".", "ar_JO-kareem-low"),
    "miro": create_tts_engine("vits-piper-ar_JO-SA_miro-high", "ar_JO-SA_miro-high"),
    "miro_v2": create_tts_engine("vits-piper-ar_JO-SA_miro_V2-high", "ar_JO-SA_miro_V2-high"),
    "sadi": create_tts_engine("vits-piper-ar_JO-SA_dii-high", "ar_JO-SA_dii-high")
}
local_voices = {k: v for k, v in local_voices.items() if v is not None}

# --- 2. معالجة النصوص والأرقام ---
def clean_text(text):
    # تحويل الأرقام الهندية (١٢٣) إلى عالمية (123) ليفهمها المحرك
    hindi_digits = "٠١٢٣٤٥٦٧٨٩"
    arabic_digits = "0123456789"
    text = text.translate(str.maketrans(hindi_digits, arabic_digits))
    
    # إزالة الفواصل بين الأرقام (مثل ١٬٢٧٩ لتصبح 1279)
    text = text.replace("٬", "").replace(",", "")
    
    # السماح فقط بالعربي والأرقام والنقاط
    text = re.sub(r'[^\u0621-\u064A0-9\s\.]', ' ', text)
    return " ".join(text.split())

# --- 3. وظائف التشغيل ---
@app.route('/v1/audio/speech', methods=['POST', 'OPTIONS'])
def serve_speech():
    if request.method == 'OPTIONS': return make_response('', 200)
    data = request.json
    voice_key = data.get("voice", "ar-SA-ZariyahNeural")
    input_text = clean_text(data.get("input", ""))
    
    # خيار مايكروسوفت
    if "Neural" in voice_key or "ar-" in voice_key:
        try:
            async def generate_edge():
                communicate = edge_tts.Communicate(input_text, voice_key)
                audio_bytes = b""
                async for chunk in communicate.stream():
                    if chunk["type"] == "audio": audio_bytes += chunk["data"]
                return audio_bytes
            
            audio_data = asyncio.run(generate_edge())
            return send_file(io.BytesIO(audio_data), mimetype="audio/mpeg")
        except Exception as e:
            print(f"Microsoft Error: {e}")
            voice_key = "miro" # العودة للمحلي عند الفشل

    # الخيار المحلي
    try:
        current_tts = local_voices.get(voice_key, list(local_voices.values())[0])
        chunks = [c.strip() for c in input_text.split('.') if c.strip()]
        if not chunks: chunks = [input_text]
        
        all_samples = []
        for chunk in chunks:
            audio = current_tts.generate(chunk, sid=0, speed=1.1)
            all_samples.append(audio.samples)
            
        combined = np.concatenate(all_samples)
        out = io.BytesIO()
        with wave.open(out, 'wb') as f:
            f.setnchannels(1); f.setsampwidth(2); f.setframerate(current_tts.sample_rate)
            f.writeframes((combined * 32767).astype(np.int16).tobytes())
        out.seek(0)
        return send_file(out, mimetype="audio/wav")
    except Exception:
        traceback.print_exc()
        return jsonify({"error": "Local TTS Engine Failure"}), 500

@app.route('/v1/models', methods=['GET'])
def list_models():
    res = [{"id": k, "object": "model"} for k in local_voices.keys()]
    res.append({"id": "microsoft", "object": "model"})
    return jsonify({"data": res})

if __name__ == "__main__":
    print("🚀 الخادم المستقر يعمل الآن على http://localhost:5000/v1")
    serve(app, host='0.0.0.0', port=5000)
