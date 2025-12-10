import os
import requests
import json
import time 
from flask import Flask, request, Response
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")
API_BASE_URL = "https://openrouter.ai/api/v1/chat/completions"

MODEL_NAME = "mistralai/mistral-7b-instruct:free"

MAX_RETRIES = 2
RETRY_DELAY_SECONDS = 5
FRIENDLY_ERROR_MESSAGE = "Sorry, something went wrong, please try again. The service may be busy."


def generate_payload(user_message):
    return {
        "model": MODEL_NAME,
        "messages": [
            {"role": "system", "content": "You are a friendly and helpful AI customer service agent. Please reply concisely and professionally, and your responses MUST BE IN ENGLISH. Never return empty content."},
            {"role": "user", "content": user_message}
        ],
        "stream": True  
    }

def generate_headers():
    """构建请求头"""
    return {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "X-Title": "AiKang AI Service"
    }


@app.route("/api/chat", methods=["POST"])
def chat_stream():
 
    if not OPENROUTER_API_KEY:
        app.logger.error("OPENROUTER_API_KEY 环境变量未设置。")
        return "❌ 后端配置错误：缺少 API 密钥。", 500

    try:
        data = request.get_json()
        user_message = data.get("message")

        if not user_message:
            return "❌ 请求体缺少 'message' 字段。", 400
        
        response = None
        for attempt in range(MAX_RETRIES):
            try:
                response = requests.post(
                    API_BASE_URL, 
                    headers=generate_headers(), 
                    json=generate_payload(user_message), 
                    stream=True
                )

                if response.status_code == 200:
                    # 成功，跳出重试循环
                    break

                elif response.status_code == 429:
                    app.logger.warning(f"OpenRouter 速率限制 (429)。尝试 {attempt + 1}/{MAX_RETRIES}。等待 {RETRY_DELAY_SECONDS} 秒后重试...")
                    if attempt < MAX_RETRIES - 1:
                        time.sleep(RETRY_DELAY_SECONDS) # 暂停等待
                        continue # 继续下一次循环，重试请求
                    else:
                        raise requests.exceptions.HTTPError(f"Maximum retries reached for 429 error.")

                else:
                    error_data = response.text
                    app.logger.error(f"OpenRouter API 调用失败，状态码 {response.status_code}。详情：{error_data}")
                    raise requests.exceptions.HTTPError(f"Non-429 API error: {response.status_code}")

            except requests.exceptions.RequestException as e:
                app.logger.error(f"请求 OpenRouter API 失败: {e}")
                if attempt < MAX_RETRIES - 1:
                    time.sleep(RETRY_DELAY_SECONDS)
                    continue
                else:
                    raise # 抛出网络错误，进入外部 catch 块


        if response is None or response.status_code != 200:
            raise Exception("API call failed after all retries.")


        def generate_text_stream():
            try:
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
                            except json.JSONDecodeError as e:
                                app.logger.warning(f"JSON 解析错误，跳过该块: {e}, Data: {data_part[:50]}...")
                                continue
            
                yield ''
            except requests.exceptions.ChunkedEncodingError as e:
                app.logger.error(f"流式传输中断错误 (ChunkedEncodingError): {e}")
                yield ''
            except Exception as e:
                app.logger.error(f"流处理中发生未知错误: {e}")
                yield ''


        return Response(generate_text_stream(), mimetype='text/plain')

    except Exception as e:
        app.logger.error(f"服务器处理请求时发生未知错误: {e}")
        
        return Response(
            FRIENDLY_ERROR_MESSAGE, 
            status=500, 
            mimetype='text/plain'
        )

if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=os.environ.get("PORT", 5000))
