import requests
import json
from flask import Flask, request, jsonify
from flask_cors import CORS

# 请注意：由于这是公开的示例代码，我将使用一个示例 API Key。
# 在实际部署中，强烈建议使用环境变量来保护您的 API Key。
# 示例 API Key (请替换为您自己的有效 Grok API Key)
API_KEY = "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"
GROK_MODEL = "x-ai/grok-4.1-fast:free" # 定义使用的模型

# 初始化 Flask 应用
app = Flask(__name__)
# 启用 CORS。允许前端运行在 Live Server（例如 http://127.0.0.1:5500）时，
# 可以向运行在 5000 端口的 API 发送请求。
CORS(app) 

# ===============================================
# 核心 Grok API 调用函数 (从您的原始代码中提取和优化)
# ===============================================

def ask_grok(question):
    """
    负责调用 OpenRouter 上的 Grok API 获取回复。
    """
    url = "https://openrouter.ai/api/v1/chat/completions"

    headers = {
        # 注意 f-string 的使用，确保 API Key 被正确传递
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }

    data = {
        "model": GROK_MODEL,
        "messages": [
            {"role": "user", "content": question}
        ]
    }

    try:
        # 发送 POST 请求到 Grok API
        response = requests.post(url, headers=headers, json=data, timeout=30) 
        
        # 检查 HTTP 状态码
        if response.status_code == 200:
            res_json = response.json()
            # 确保结果结构存在
            if res_json.get("choices") and res_json["choices"][0].get("message"):
                return res_json["choices"][0]["message"]["content"]
            else:
                print("Error: API response format is unexpected.")
                return "抱歉，AI 接口返回了意外的格式。"
        else:
            print(f"Error Status Code: {response.status_code}")
            print(f"API Error Details: {response.text}")
            return f"Error: API 调用失败，状态码 {response.status_code}。"
            
    except requests.exceptions.RequestException as e:
        # 处理网络连接或超时错误
        print(f"Request Error: {e}")
        return "抱歉，网络连接失败或超时。"


# ===============================================
# Flask API 路由：这是前端调用的接口
# ===============================================

@app.route('/api/chat', methods=['POST'])
def handle_chat():
    """
    处理来自前端的 POST 请求，提取用户消息，调用 Grok，并返回 JSON 响应。
    """
    
    # 1. 获取前端发送的 JSON 数据
    try:
        data = request.get_json()
        user_message = data.get('message')
    except Exception:
        # 如果 JSON 格式不正确，返回 400 错误
        return jsonify({'response': 'API Error: 请求体格式错误，需要 JSON 格式。'}), 400

    # 2. 检查消息内容是否缺失
    if not user_message:
        return jsonify({'response': 'API Error: 缺少 "message" 字段。'}), 400

    # 3. 调用 Grok API 获取回复
    grok_response = ask_grok(user_message)
    
    # 4. 将回复封装成 JSON 结构返回给前端
    return jsonify({
        'response': grok_response
    })



if __name__ == '__main__':
    
    print("Flask Grok API Server is starting...")
    app.run(debug=True, port=5000)