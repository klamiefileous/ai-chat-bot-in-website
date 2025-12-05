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
# 原 Grok 模型 x-ai/grok-4.1-fast:free 已不可用。
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
                {"role": "system", "content": "你是一个友好、乐于助人的中文 AI 客服，请使用中文简洁回复。"},
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
        # stream=True 是 requests 库用于处理流式响应的关键
        response = requests.post(API_BASE_URL, headers=headers, json=payload, stream=True)

        # 检查 API 响应状态码
        if response.status_code != 200:
            # 如果 OpenRouter 返回非 200，记录错误详情并向前端返回 500 错误
            error_data = response.text
            app.logger.error(f"OpenRouter API 调用失败，状态码 {response.status_code}。详情：{error_data}")
            
            # 向前端返回 500 错误，包含 API 错误信息
            return Response(
                f"❌ Grok API 调用失败，状态码 {response.status_code}。详情：{error_data}", 
                status=500, 
                mimetype='text/plain'
            )

        # 成功：定义生成器函数，用于流式发送数据给前端
        def generate():
            for chunk in response.iter_content(chunk_size=1024):
                if chunk:
                    # OpenRouter 返回的是 SSE (Server-Sent Events) 格式，我们需要原样转发
                    # 每个 chunk 通常以 data: {json_payload} 结束
                    try:
                        yield chunk
                    except Exception as e:
                        app.logger.error(f"在流式传输中发生错误: {e}")
                        break

        # 返回流式响应
        return Response(generate(), mimetype='text/event-stream')

    except Exception as e:
        app.logger.error(f"服务器处理请求时发生未知错误: {e}")
        return f"❌ 服务器处理请求时发生未知错误：{e}", 500

if __name__ == "__main__":
    # 在生产环境中，Render 将使用 Gunicorn 或类似的 WSGI 服务器来运行应用
    # 这里的运行仅用于本地测试
    app.run(debug=True, host='0.0.0.0', port=os.environ.get("PORT", 5000))
