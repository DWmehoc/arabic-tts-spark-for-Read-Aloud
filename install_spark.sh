#!/bin/bash

PROJECT_DIR="$HOME/arabic_tts_spark"
echo "🌟 جاري تثبيت نظام Spark TTS وتحميل الأصوات..."

# 1. تنصيب المتطلبات
sudo apt-get update && sudo apt-get install -y python3-pip python3-dev tar bzip2 wget

# 2. إنشاء المجلد والدخول إليه
mkdir -p "$PROJECT_DIR"
cd "$PROJECT_DIR"

# 3. روابط الأصوات التي قدمتها
MODELS=(
"https://github.com/k2-fsa/sherpa-onnx/releases/download/tts-models/vits-piper-ar_JO-SA_dii-high.tar.bz2"
"https://github.com/k2-fsa/sherpa-onnx/releases/download/tts-models/vits-piper-ar_JO-SA_miro-high.tar.bz2"
"https://github.com/k2-fsa/sherpa-onnx/releases/download/tts-models/vits-piper-ar_JO-SA_miro_V2-high.tar.bz2"
"https://github.com/k2-fsa/sherpa-onnx/releases/download/tts-models/vits-piper-ar_JO-kareem-medium.tar.bz2"
)

# 4. تحميل وفك ضغط الأصوات تلقائياً
echo "📥 جاري تحميل الموديلات الصوتية (قد يستغرق ذلك وقتاً)..."
for url in "${MODELS[@]}"; do
    file_name=$(basename "$url")
    if [ ! -f "$file_name" ]; then
        echo "تحميل $file_name..."
        wget -q "$url"
        echo "فك ضغط $file_name..."
        tar -xjf "$file_name"
    else
        echo "$file_name موجود مسبقاً، تخطي التحميل."
    fi
done

# 5. تنصيب مكتبات بايثون
pip3 install flask flask-cors waitress numpy sherpa-onnx edge-tts --break-system-packages

echo "✅ اكتملت العملية! الموديلات الآن جاهزة والسيرفر معد للعمل."
