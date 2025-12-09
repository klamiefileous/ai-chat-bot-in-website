import os
import requests
import json
from flask import Flask, request, Response
from flask_cors import CORS

app = Flask(__name__)


CORS(app)

OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")
API_BASE_URL = "https://openrouter.ai/api/v1/chat/completions"


MODEL_NAME = "mistralai/mistral-7b-instruct:free" 



@app.route("/api/chat", methods=["POST"])
def chat_stream():
    """
    接收用户消息，调用 OpenRouter API，并以流式方式返回响应。
    """
    if not OPENROUTER_API_KEY:
        app.logger.error("OPENROUTER_API_KEY 环境变量未设置。")
        return "❌ 后端配置错误：缺少 API 密钥。", 500

    try:
        data = request.get_json()
        user_message = data.get("message")

        if not user_message:
            return "❌ 请求体缺少 'message' 字段。", 400

        payload = {
            "model": MODEL_NAME,
            "messages": [
                {"role": "system", "content": "You are a friendly and helpful AI customer service agent. Please reply concisely and professionally, and your responses MUST BE IN ENGLISH. Never return empty content."},
                {"role": "user", "content": user_message}
            ],
            "stream": True # 开启流式传输
        }

        
        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
            "X-Title": "AiKang AI Service" # 可选：用于 OpenRouter 统计
        }

        
        response = requests.post(API_BASE_URL, headers=headers, json=payload, stream=True)

        if response.status_code != 200:
            error_data = response.text
            app.logger.error(f"OpenRouter API 调用失败，状态码 {response.status_code}。详情：{error_data}")
            return Response(
                f"❌ Grok API 调用失败，状态码 {response.status_code}。详情：{error_data}", 
                status=500, 
                mimetype='text/plain'
            )

        def generate_text_stream():
            for line in response.iter_lines():
                if line:
                    decoded_line = line.decode('utf-8')
                    if decoded_line.startswith('data: '):
                        data_part = decoded_line[6:].strip()
        
                        
                        if data_part == '[DONE]':
                            break
                        
                        try:
                            chunk = json.loads(data_part)
                            content = chunk['choices'][0]['delta'].get('content', '')
                            if content:
                                yield content
                        except json.JSONDecodeError:
                            continue
                    
            yield ''

        return Response(generate_text_stream(), mimetype='text/plain')

    except Exception as e:
        app.logger.error(f"服务器处理请求时发生未知错误: {e}")
        return f"❌ 服务器处理请求时发生未知错误：{e}", 500

if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=os.environ.get("PORT", 5000))

