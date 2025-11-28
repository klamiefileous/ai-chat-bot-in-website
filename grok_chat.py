import requests
import json
import os # 导入 os 模块，用于读取环境变量

from flask import Flask, request, jsonify
from flask_cors import CORS

# ===============================================
# 1. 配置和初始化
# ===============================================

# 从 Render 环境变量中获取 API Key。
# 注意：Render 中设置的 Key 必须命名为 GROK_API_KEY
API_KEY = os.environ.get("GROK_API_KEY") 

# 如果在本地测试，可以取消注释下面两行，使用硬编码的 Key：
# if not API_KEY:
#     API_KEY = "sk-or-v1-xxxxxxxxxxxxxxxxx" # 替换为您的真实 Key

GROK_MODEL = "x-ai/grok-4.1-fast:free" 

# 初始化 Flask 应用
app = Flask(__name__)
# 启用 CORS，允许前端（如 Netlify）访问
CORS(app) 

# ===============================================
# 2. 核心 Grok API 调用函数
# ===============================================

def ask_grok(question):
    """
    负责调用 OpenRouter 上的 Grok API 获取回复。
    """
    if not API_KEY:
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
        ]
    }

    try:
        response = requests.post(url, headers=headers, json=data, timeout=30) 
        
        if response.status_code == 200:
            res_json = response.json()
            if res_json.get("choices") and res_json["choices"][0].get("message"):
                return res_json["choices"][0]["message"]["content"]
            else:
                return "抱歉，AI 接口返回了意外的格式。"
        else:
            print(f"API Error Details: {response.text}")
            return f"错误：API 调用失败，状态码 {response.status_code}。"
            
    except requests.exceptions.RequestException as e:
        print(f"Request Error: {e}")
        return "抱歉，网络连接失败或超时。"


# ===============================================
# 3. Flask API 路由
# ===============================================

@app.route('/api/chat', methods=['POST'])
def handle_chat():
    """
    处理来自前端的 POST 请求。
    """
    
    try:
        data = request.get_json()
        user_message = data.get('message')
    except Exception:
        return jsonify({'response': 'API Error: 请求体格式错误。'}), 400

    if not user_message:
        return jsonify({'response': 'API Error: 缺少 "message" 字段。'}), 400

    # 调用 Grok API 获取回复
    grok_response = ask_grok(user_message)
    
    # 将回复封装成 JSON 结构返回给前端
    return jsonify({
        'response': grok_response
    })


# ===============================================
# 4. 运行 Flask 应用 (Render 部署不需要这个 if 块，但本地测试需要)
# ===============================================
if __name__ == '__main__':
    print("Flask Grok API Server is starting...")
    # 注意：在本地运行时，如果未设置环境变量，此应用可能无法调用 API。
    app.run(debug=True, port=5000)
