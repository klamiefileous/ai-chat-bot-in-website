import requests
import json
import os
from flask import Flask, request, Response
from flask_cors import CORS

# --- 配置 ---
# 从 Render 环境变量中获取 API 密钥
API_KEY = os.environ.get("GROK_API_KEY") 
GROK_MODEL = "x-ai/grok-4.1-fast:free" 

app = Flask(__name__)
# 启用 CORS，允许前端（Netlify）跨域访问
CORS(app) 

# --- 核心函数：与 Grok API 进行流式通信 ---
def ask_grok(question):
    """
    调用 OpenRouter Grok API，并以流式方式返回响应。
    """
    if not API_KEY:
        # 如果密钥缺失，返回错误字符串
        return "错误：API 密钥未设置或未从环境变量中读取。"

    url = "https://openrouter.ai/api/v1/chat/completions"

    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }

    data = {
        "model": GROK_MODEL,
        "messages": [
            {"role": "user", "content": question}
        ],
        # 启用流式传输是实现实时回复的关键
        "stream": True 
    }

    try:
        # 发起请求时设置 stream=True，以便实时读取数据
        response = requests.post(url, headers=headers, json=data, stream=True, timeout=120) 
        
        # 如果 API 返回了非 200 错误码（例如 401 认证失败）
        if response.status_code != 200:
            print(f"API Error Details (Non-Streaming): {response.text}")
            # 返回错误信息（非流式）
            return f"错误：API 调用失败，状态码 {response.status_code}。详情：{response.text}"


        # --- 生成器函数：实时处理和发送流数据 ---
        def generate():
            # 逐行读取 API 的流式响应
            for line in response.iter_lines():
                if line:
                    decoded_line = line.decode('utf-8')
                    # API 流式数据以 'data: ' 开头
                    if decoded_line.startswith('data: '):
                        data_chunk = decoded_line[6:]
                        
                        # 检查是否为结束标记
                        if data_chunk.strip() == '[DONE]':
                            break 
                        
                        try:
                            res_json = json.loads(data_chunk)
                            # 提取 AI 生成的文本内容
                            content = res_json['choices'][0]['delta'].get('content', '')
                            
                            # 将提取到的内容块作为流的一部分 yield（发送）给前端
                            yield content 
                        except json.JSONDecodeError:
                            # 忽略无法解析的行
                            continue
        
        # 关键：将生成器函数封装成 Flask Response，以 text/plain 格式流式返回
        return Response(generate(), mimetype='text/plain')
        
    except requests.exceptions.RequestException as e:
        # 网络连接或超时错误
        print(f"Request Error: {e}")
        return "抱歉，网络连接失败或超时。"

# --- 路由：处理来自前端的聊天请求 ---
@app.route('/api/chat', methods=['POST'])
def handle_chat():
    """
    处理来自前端的 POST 请求，并返回流式或错误响应。
    """
    try:
        data = request.get_json()
        user_message = data.get('message')
    except Exception:
        # 如果请求体不是有效的 JSON
        return "API Error: 请求体格式错误。", 400

    if not user_message:
        return "API Error: 缺少 'message' 字段。", 400

    # 关键：直接返回 ask_grok 的结果，它现在是流式响应（Response 对象）
    return ask_grok(user_message)


if __name__ == '__main__':
    print("Flask Grok API Server is starting...")
    # 在本地运行，端口为 5000
    app.run(debug=True, port=5000)
