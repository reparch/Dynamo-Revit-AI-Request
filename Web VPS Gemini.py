from flask import Flask, request, jsonify, render_template_string
import requests
import json
import os
app = Flask(__name__)

# --- Настройки ---
API_KEY = "ВАШ_API_КЛЮЧ"
MODEL = "gemini-3.5-flash"
API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent?key={API_KEY}"
COUNT_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:countTokens?key={API_KEY}"
HISTORY_FILE = "chat_history.json"

def load_history():
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return []
    return []

def save_history(history):
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)

chat_history = load_history()

# --- Вспомогательная функция для точного подсчета токенов ---
def get_tokens_count(text):
    if not text: return 0
    payload = {"contents": [{"parts": [{"text": text}]}]}
    try:
        res = requests.post(COUNT_URL, headers={"Content-Type": "application/json"}, json=payload)
        if res.status_code == 200:
            return res.json().get("totalTokens", 0)
    except Exception:
        pass
    return 0

# --- HTML и JavaScript интерфейс ---
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>BIM Assistant | Revit & Automation</title>
    <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
    <style>
        body { font-family: sans-serif; max-width: 850px; margin: 30px auto; padding: 20px; background-color: #f4f6f9; }
        .controls { background: white; padding: 15px; border-radius: 8px; margin-bottom: 15px; border: 1px solid #ddd; display: flex; gap: 25px; align-items: center; flex-wrap: wrap; }
        .control-group { display: flex; flex-direction: column; gap: 5px; }
        select { padding: 6px; border-radius: 4px; border: 1px solid #ccc; font-size: 14px; }
        .temp-container { min-width: 220px; }
        .temp-slider-wrap { display: flex; flex-direction: column; gap: 4px; }
        .ticks { display: flex; justify-content: space-between; font-size: 11px; color: #666; padding: 0 4px; }
        #chatbox { height: 450px; background: white; border: 1px solid #ccc; border-radius: 8px; overflow-y: auto; padding: 15px; margin-bottom: 15px; }
        .msg { margin-bottom: 15px; line-height: 1.5; }
        .user { color: #2c3e50; font-weight: bold; white-space: pre-wrap; word-wrap: break-word; font-family: monospace; font-size: 14px; }
        .bot { color: #16a085; }
        .bot p { margin: 5px 0; }
        .bot ul, .bot ol { padding-left: 20px; margin: 5px 0; }
        .bot pre { background: #f0f2f5; padding: 10px; border-radius: 5px; overflow-x: auto; color: #333; }
        .token-badge { display: flex; flex-direction: column; gap: 10px; align-items: flex-start; font-size: 12px; color: #495057; background: #f8f9fa; padding: 12px; border-radius: 6px; margin-top: 12px; font-family: sans-serif; border: 1px solid #dee2e6; }
        .token-details { font-size: 11px; color: #6c757d; margin-top: 4px; margin-left: 20px; display: flex; flex-direction: column; gap: 2px; }
        .token-output { color: #198754; background: #e8f8f5; padding: 3px 8px; border-radius: 4px; font-weight: bold; border: 1px solid #a9dfbf; }
        .input-area { display: flex; gap: 10px; align-items: flex-start; }
        textarea { flex-grow: 1; padding: 10px; border: 1px solid #ccc; border-radius: 4px; font-size: 14px; resize: vertical; min-height: 44px; font-family: monospace; }
        button { padding: 10px 20px; background-color: #2980b9; color: white; border: none; border-radius: 4px; cursor: pointer; font-size: 14px; height: 44px; white-space: nowrap; }
        button:hover { background-color: #3498db; }
        .clear-btn { background-color: #e74c3c; }
        .clear-btn:hover { background-color: #c0392b; }
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
        <div class="control-group temp-container">
            <label for="tempSlider"><b>Температура:</b> <span id="tempValue" style="color: #2980b9; font-weight: bold;">0.7</span></label>
            <div class="temp-slider-wrap">
                <input type="range" id="tempSlider" min="0" max="2" step="1" value="1" oninput="updateTemperature(this.value)">
                <div class="ticks">
                    <span>0.0</span>
                    <span>0.7</span>
                    <span>1.2</span>
                </div>
            </div>
        </div>
    </div>

    <div id="chatbox"></div>
    
    <div class="input-area">
        <textarea id="userInput" rows="3" placeholder="Вставьте код или вопрос (Shift+Enter для новой строки, Enter для отправки)..." onkeydown="handleKeyPress(event)"></textarea>
        <button onclick="sendMessage()">Отправить</button>
        <button class="clear-btn" onclick="clearHistory()">Очистить чат</button>
    </div>

    <script>
        const tempSteps = [0.0, 0.7, 1.2];

        window.onload = async function() {
            try {
                const response = await fetch('/history');
                const history = await response.json();
                const chatbox = document.getElementById('chatbox');
                
                history.forEach(msg => {
                    const text = msg.parts[0].text;
                    if (msg.role === 'user') {
                        const safeText = text.replace(/</g, "&lt;").replace(/>/g, "&gt;");
                        chatbox.innerHTML += `<div class="msg user">Вы:<br>${safeText}</div>`;
                    } else if (msg.role === 'model') {
                        const formattedAnswer = marked.parse(text);
                        chatbox.innerHTML += `<div class="msg bot"><b style="font-family:sans-serif;">Gemini:</b><br>${formattedAnswer}</div><hr>`;
                    }
                });
                chatbox.scrollTop = chatbox.scrollHeight;
            } catch (error) {
                console.error("Ошибка загрузки истории:", error);
            }
        };

        function updateTemperature(index) {
            document.getElementById('tempValue').innerText = tempSteps[index];
        }

        async function sendMessage() {
            const input = document.getElementById('userInput');
            const text = input.value;
            if (!text.trim()) return;
            
            const length = document.getElementById('lengthSelect').value;
            const style = document.getElementById('styleSelect').value;
            const tempIndex = document.getElementById('tempSlider').value;
            const temperature = tempSteps[tempIndex];

            const chatbox = document.getElementById('chatbox');
            const safeText = text.replace(/</g, "&lt;").replace(/>/g, "&gt;");
            
            chatbox.innerHTML += `<div class="msg user">Вы: <span style="font-weight:normal; font-size:12px; color:#888; font-family:sans-serif;">[${length}, ${style}, T=${temperature}]</span><br>${safeText}</div>`;
            input.value = '';
            chatbox.scrollTop = chatbox.scrollHeight;

            try {
                const response = await fetch('/ask', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ 
                        prompt: text, 
                        length: length, 
                        style: style,
                        temperature: temperature
                    })
                });
                
                const data = await response.json();
                const formattedAnswer = marked.parse(data.answer);
                
                let tokenInfoHtml = '';
                if (data.tokens) {
                    tokenInfoHtml = `
                        <div class="token-badge">
                            <div>
                                📥 <b>Входящий контекст: ${data.tokens.input} токенов</b>
                                <div class="token-details">
                                    <span>• Системные настройки: <b>${data.tokens.sys}</b></span>
                                    <span>• Память (история переписки): <b>${data.tokens.hist}</b></span>
                                    <span>• Ваш новый запрос: <b>${data.tokens.new}</b></span>
                                </div>
                            </div>
                            <div class="token-output">📤 Текущий ответ ИИ (генерация): ${data.tokens.output}</div>
                            <div>📊 <b>Итого за операцию: ${data.tokens.total}</b></div>
                        </div>
                    `;
                }

                chatbox.innerHTML += `
                    <div class="msg bot">
                        <b style="font-family:sans-serif;">Gemini:</b><br>${formattedAnswer}
                        ${tokenInfoHtml}
                    </div>
                    <hr>
                `;
            } catch (error) {
                chatbox.innerHTML += `<div class="msg bot" style="color: red;"><b>Ошибка соединения с сервером.</b></div><hr>`;
            }
            
            chatbox.scrollTop = chatbox.scrollHeight;
        }

        async function clearHistory() {
            if (!confirm("Вы уверены, что хотите удалить историю диалога?")) return;
            await fetch('/clear_history', { method: 'POST' });
            document.getElementById('chatbox').innerHTML = '';
        }

        function handleKeyPress(e) {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendMessage();
            }
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

def ask_gemini(current_history, length, style, temperature):
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

    # Замеряем токены отдельных частей
    sys_tokens = get_tokens_count(system_instruction)
    new_request_text = current_history[-1]["parts"][0]["text"]
    new_tokens = get_tokens_count(new_request_text)

    headers = {"Content-Type": "application/json"}
    payload = {
        "system_instruction": {
            "parts": [{"text": system_instruction}]
        },
        "contents": current_history,
        "generationConfig": {
            "temperature": float(temperature)
        }
    }

    response = requests.post(API_URL, headers=headers, json=payload)
    if response.status_code == 200:
        res_json = response.json()
        try:
            answer_text = res_json["candidates"][0]["content"]["parts"][0]["text"]
            usage = res_json.get("usageMetadata", {})
            
            input_total = usage.get("promptTokenCount", 0)
            # Высчитываем историю вычитанием. Функция max(0, ...) страхует от отрицательных значений
            hist_tokens = max(0, input_total - sys_tokens - new_tokens)
            
            tokens_data = {
                "input": input_total,
                "sys": sys_tokens,
                "hist": hist_tokens,
                "new": new_tokens,
                "output": usage.get("candidatesTokenCount", 0),
                "total": usage.get("totalTokenCount", 0)
            }
            return answer_text, tokens_data
        except (KeyError, IndexError):
            return "Ошибка при обработке ответа от API.", None
            
    return f"Ошибка {response.status_code}: {response.text}", None

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/history', methods=['GET'])
def get_history():
    return jsonify(chat_history)

@app.route('/clear_history', methods=['POST'])
def clear_history():
    global chat_history
    chat_history = []
    save_history(chat_history)
    return jsonify({"status": "success"})

@app.route('/ask', methods=['POST'])
def ask():
    global chat_history
    
    data = request.json
    user_prompt = data.get('prompt')
    length = data.get('length', 'сжатый')
    style = data.get('style', 'формальный')
    temperature = data.get('temperature', 0.7)
    
    display_text = user_prompt
    api_text = user_prompt

    # Перехват кодового слова
    if user_prompt.strip().lower() == "многабукав":
        # Слово "Revit" + пробел считается как 1 токен. 
        # Добавляем префикс, чтобы модель поняла, что с этим делать.
        api_text = "Проигнорируй этот мусор и просто скажи, что успешно переварил гигантский запрос. " + "Revit " * 1050000
        display_text = "многабукав [В запрос скрыто интегрирован массив на ~1.05 млн токенов]"
    
    # Сохраняем в интерфейс и JSON-файл компактный вариант
    chat_history.append({
        "role": "user",
        "parts": [{"text": display_text}]
    })
    
    # Создаем временную копию истории для отправки тяжелого запроса в API
    history_for_api = chat_history.copy()
    history_for_api[-1] = {
        "role": "user",
        "parts": [{"text": api_text}]
    }
    
    # Отправляем в функцию тяжелый массив (history_for_api), а не оригинальный
    answer, tokens = ask_gemini(history_for_api, length, style, temperature)
    
    if tokens is not None:
        chat_history.append({
            "role": "model",
            "parts": [{"text": answer}]
        })
        save_history(chat_history)
    else:
        chat_history.pop()
    
    return jsonify({'answer': answer, 'tokens': tokens})

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)
