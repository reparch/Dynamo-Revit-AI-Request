from flask import Flask, request, jsonify, render_template_string
import requests

app = Flask(__name__)

# --- Настройки ---
API_KEY = "ВАШ_API_КЛЮЧ"
MODEL = "gemini-3.5-flash-lite"
API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent?key={API_KEY}"

# --- HTML и JavaScript интерфейс ---
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>BIM Assistant | Revit & Automation</title>
    <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
    <style>
        body { font-family: sans-serif; max-width: 800px; margin: 30px auto; padding: 20px; background-color: #f4f6f9; }
        .controls { background: white; padding: 15px; border-radius: 8px; margin-bottom: 15px; border: 1px solid #ddd; display: flex; gap: 20px; flex-wrap: wrap; }
        .control-group { display: flex; flex-direction: column; gap: 5px; }
        select { padding: 6px; border-radius: 4px; border: 1px solid #ccc; font-size: 14px; }
        #chatbox { height: 450px; background: white; border: 1px solid #ccc; border-radius: 8px; overflow-y: auto; padding: 15px; margin-bottom: 15px; }
        .msg { margin-bottom: 15px; line-height: 1.5; }
        /* white-space: pre-wrap сохраняет все табы и переносы строк пользователя */
        .user { color: #2c3e50; font-weight: bold; white-space: pre-wrap; word-wrap: break-word; font-family: monospace; font-size: 14px; }
        .bot { color: #16a085; }
        .bot p { margin: 5px 0; }
        .bot ul, .bot ol { padding-left: 20px; margin: 5px 0; }
        .input-area { display: flex; gap: 10px; align-items: flex-start; }
        textarea { flex-grow: 1; padding: 10px; border: 1px solid #ccc; border-radius: 4px; font-size: 14px; resize: vertical; min-height: 44px; font-family: monospace; }
        button { padding: 10px 20px; background-color: #2980b9; color: white; border: none; border-radius: 4px; cursor: pointer; font-size: 14px; height: 44px; }
        button:hover { background-color: #3498db; }
    </style>
</head>
<body>
    <h2>BIM Ассистент (Revit & Automation)</h2>
    
    <div class="controls">
        <div class="control-group">
            <label for="lengthSelect"><b>Длина ответа:</b></label>
            <select id="lengthSelect">
                <option value="сжатый">Сжатый (без воды, тезисно)</option>
                <option value="расширенный">Расширенный (подробно + рекомендации)</option>
            </select>
        </div>
        <div class="control-group">
            <label for="styleSelect"><b>Стиль ответа:</b></label>
            <select id="styleSelect">
                <option value="формальный">Формальный (профессиональный)</option>
                <option value="френдли">Френдли (бро, дружище)</option>
            </select>
        </div>
    </div>

    <div id="chatbox"></div>
    
    <div class="input-area">
        <textarea id="userInput" rows="3" placeholder="Вставьте код или текст (Shift+Enter для новой строки, Enter для отправки)..." onkeydown="handleKeyPress(event)"></textarea>
        <button onclick="sendMessage()">Отправить</button>
    </div>

    <script>
        async function sendMessage() {
            const input = document.getElementById('userInput');
            const text = input.value;
            if (!text.trim()) return;
            
            const length = document.getElementById('lengthSelect').value;
            const style = document.getElementById('styleSelect').value;

            const chatbox = document.getElementById('chatbox');
            // Экранируем HTML-теги, чтобы код со скобками < > отображался как текст
            const safeText = text.replace(/</g, "&lt;").replace(/>/g, "&gt;");
            
            chatbox.innerHTML += `<div class="msg user">Вы: <span style="font-weight:normal; font-size:12px; color:#888; font-family:sans-serif;">[${length}, ${style}]</span><br>${safeText}</div>`;
            input.value = '';
            chatbox.scrollTop = chatbox.scrollHeight;

            try {
                const response = await fetch('/ask', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ prompt: text, length: length, style: style })
                });
                
                const data = await response.json();
                const formattedAnswer = marked.parse(data.answer);
                chatbox.innerHTML += `<div class="msg bot"><b style="font-family:sans-serif;">Gemini:</b><br>${formattedAnswer}</div><hr>`;
            } catch (error) {
                chatbox.innerHTML += `<div class="msg bot" style="color: red;"><b>Ошибка соединения с сервером.</b></div><hr>`;
            }
            
            chatbox.scrollTop = chatbox.scrollHeight;
        }

        function handleKeyPress(e) {
            // Отправка по Enter (без зажатого Shift)
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendMessage();
            }
            // Обработка Tab для вставки пробелов (4 пробела) вместо потери фокуса
            if (e.key === 'Tab') {
                e.preventDefault();
                const target = e.target;
                const start = target.selectionStart;
                const end = target.selectionEnd;
                target.value = target.value.substring(0, start) + "    " + target.value.substring(end);
                target.selectionStart = target.selectionEnd = start + 4;
            }
        }
    </script>
</body>
</html>
"""

# --- Логика запроса к Gemini с системным промптом ---
def ask_gemini(prompt, length, style):
    system_instruction = (
        "Ты — BIM-ассистент, эксперт по Autodesk Revit, Dynamo, Python и автоматизации проектирования.\n"
        "Отвечай на любые вопросы, связанные с Revit, моделированием, плагинами и скриптами.\n"
        "Если пользователь задает вопрос на сторонние темы, не связанные с проектированием и BIM (например, кулинария, политика, автомобили общего характера), "
        "вежливо отвечай, что это не в твоей компетенции.\n\n"
        f"ПАРАМЕТРЫ ФОРМАТИРОВАНИЯ:\n"
        f"1. Длина ответа: {length.upper()}\n"
        "   - 'сжатый': коротко, четко, тезисно, без лишней воды.\n"
        "   - 'расширенный': подробное описание алгоритма, разбор нюансов и полезные рекомендации.\n"
        f"2. Стиль ответа: {style.upper()}\n"
        "   - СТИЛЬ 'формальный': СТРОГО запрещены любые приветствия вроде 'Привет', сленг и фамильярные обращения ('друг', 'дружище', 'бро'). Только строгий, профессиональный и деловой тон.\n"
        "   - СТИЛЬ 'френдли': дружелюбный тон повествования, допускаются и приветствуются неформальные обращения ('друг', 'дружище', 'бро')."
    )

    headers = {"Content-Type": "application/json"}
    payload = {
        "system_instruction": {
            "parts": [{"text": system_instruction}]
        },
        "contents": [{
            "parts": [{"text": prompt}]
        }]
    }

    response = requests.post(API_URL, headers=headers, json=payload)
    if response.status_code == 200:
        res_json = response.json()
        try:
            return res_json["candidates"][0]["content"]["parts"][0]["text"]
        except (KeyError, IndexError):
            return "Ошибка при обработке ответа от API."
    return f"Ошибка {response.status_code}: {response.text}"

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/ask', methods=['POST'])
def ask():
    data = request.json
    user_prompt = data.get('prompt')
    length = data.get('length', 'сжатый')
    style = data.get('style', 'формальный')
    
    answer = ask_gemini(user_prompt, length, style)
    return jsonify({'answer': answer})

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)
