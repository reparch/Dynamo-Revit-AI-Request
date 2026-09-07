from flask import Flask, request, jsonify, render_template_string
import requests

app = Flask(__name__)

# --- Настройки ---
API_KEY = "ВАШ_API_КЛЮЧ"
MODEL = "gemini-3.6-flash"
API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent?key={API_KEY}"

# --- HTML и JavaScript интерфейс с поддержкой Markdown ---
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Gemini Web Chat</title>
    <!-- Подключаем библиотеку для рендеринга Markdown -->
    <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
    <style>
        body { font-family: sans-serif; max-width: 700px; margin: 40px auto; padding: 20px; background-color: #f9f9f9; }
        #chatbox { height: 450px; background: white; border: 1px solid #ccc; border-radius: 8px; overflow-y: auto; padding: 15px; margin-bottom: 15px; }
        .msg { margin-bottom: 15px; line-height: 1.5; }
        .user { color: #2c3e50; }
        .bot { color: #16a085; }
        .bot p { margin: 5px 0; } /* Аккуратные отступы для параграфов от Markdown */
        .bot ul, .bot ol { padding-left: 20px; margin: 5px 0; }
        .input-area { display: flex; gap: 10px; }
        input { flex-grow: 1; padding: 10px; border: 1px solid #ccc; border-radius: 4px; font-size: 14px; }
        button { padding: 10px 20px; background-color: #2980b9; color: white; border: none; border-radius: 4px; cursor: pointer; font-size: 14px; }
        button:hover { background-color: #3498db; }
    </style>
</head>
<body>
    <h2>Чат с Gemini</h2>
    <div id="chatbox"></div>
    <div class="input-area">
        <input type="text" id="userInput" placeholder="Введите сообщение..." onkeypress="handleKeyPress(event)">
        <button onclick="sendMessage()">Отправить</button>
    </div>

    <script>
        async function sendMessage() {
            const input = document.getElementById('userInput');
            const text = input.value.trim();
            if (!text) return;
            
            const chatbox = document.getElementById('chatbox');
            // Добавляем сообщение пользователя
            chatbox.innerHTML += `<div class="msg user"><b>Вы:</b> ${text}</div>`;
            input.value = '';
            chatbox.scrollTop = chatbox.scrollHeight;

            // Отправляем запрос на наш Python-сервер
            try {
                const response = await fetch('/ask', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ prompt: text })
                });
                
                const data = await response.json();
                
                // Рендерим Markdown-ответ в красивый HTML с помощью marked.parse()
                const formattedAnswer = marked.parse(data.answer);
                chatbox.innerHTML += `<div class="msg bot"><b>Gemini:</b><br>${formattedAnswer}</div><hr>`;
            } catch (error) {
                chatbox.innerHTML += `<div class="msg bot" style="color: red;"><b>Ошибка соединения с сервером.</b></div><hr>`;
            }
            
            chatbox.scrollTop = chatbox.scrollHeight;
        }

        function handleKeyPress(e) {
            if (e.key === 'Enter') sendMessage();
        }
    </script>
</body>
</html>
"""

# --- Логика запроса к Gemini ---
def ask_gemini(prompt):
    headers = {"Content-Type": "application/json"}
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    response = requests.post(API_URL, headers=headers, json=payload)
    if response.status_code == 200:
        return response.json()["candidates"][0]["content"]["parts"][0]["text"]
    return f"Ошибка {response.status_code}: {response.text}"

# --- Маршрутизация Web-сервера ---
@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/ask', methods=['POST'])
def ask():
    user_prompt = request.json.get('prompt')
    answer = ask_gemini(user_prompt)
    return jsonify({'answer': answer})

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)