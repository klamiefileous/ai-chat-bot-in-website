import os
import requests
import json
from flask import Flask, request, Response
from flask_cors import CORS

app = Flask(__name__)

# 允许所有来源进行跨域请求 (CORS)
CORS(app)

# 确保在 Render 环境变量中设置了 OPENROUTER_API_KEY
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")
API_BASE_URL = "https://openrouter.ai/api/v1/chat/completions"

# ⚠️ 修复：切换到 OpenRouter 上更稳定且常用的免费模型 Mistral 7B Instruct。
MODEL_NAME = "mistralai/mistral-7b-instruct:free" 

# ----------------- 核心流式聊天路由 -----------------

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

        # 构建发送给 OpenRouter 的请求负载
        payload = {
            "model": MODEL_NAME,
            "messages": [
                # 增强 System 提示，要求模型必须使用【英文】回复
                {"role": "system", "content": "You are a friendly and helpful AI customer service agent. Please reply concisely and professionally, and your responses MUST BE IN ENGLISH. Never return empty content."},
                {"role": "user", "content": user_message}
            ],
            "stream": True # 开启流式传输
        }

        # 设置 API 请求头
        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
            "X-Title": "AiKang AI Service" # 可选：用于 OpenRouter 统计
        }

        # 发起流式请求
        response = requests.post(API_BASE_URL, headers=headers, json=payload, stream=True)

        # 检查 API 响应状态码
        if response.status_code != 200:
            error_data = response.text
            app.logger.error(f"OpenRouter API 调用失败，状态码 {response.status_code}。详情：{error_data}")
            return Response(
                f"❌ Grok API 调用失败，状态码 {response.status_code}。详情：{error_data}", 
                status=500, 
                mimetype='text/plain'
            )

        # 核心修复：解析 SSE 数据流，只转发纯文本内容
        def generate_text_stream():
            # 使用 response.iter_lines() 确保按行处理数据
            for line in response.iter_lines():
                if line:
                    decoded_line = line.decode('utf-8')
                    if decoded_line.startswith('data: '):
                        data_part = decoded_line[6:].strip()
                        
                        # 检查是否是结束标记
                        if data_part == '[DONE]':
                            break
                        
                        try:
                            chunk = json.loads(data_part)
                            # 提取模型生成的文本片段
                            content = chunk['choices'][0]['delta'].get('content', '')
                            if content:
                                yield content
                        except json.JSONDecodeError:
                            # 忽略无法解析的行
                            continue
                    
            # 确保流结束
            yield ''

        # 返回流式响应，这次只包含纯文本
        return Response(generate_text_stream(), mimetype='text/plain')

    except Exception as e:
        app.logger.error(f"服务器处理请求时发生未知错误: {e}")
        return f"❌ 服务器处理请求时发生未知错误：{e}", 500

if __name__ == "__main__":
    # 在生产环境中，Render 将使用 Gunicorn 或类似的 WSGI 服务器来运行应用
    # 这里的运行仅用于本地测试
    app.run(debug=True, host='0.0.0.0', port=os.environ.get("PORT", 5000))
