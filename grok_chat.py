import requests
import json
import os
from flask import Flask, request, Response
from flask_cors import CORS

# --- 配置 ---
# 从环境变量中获取 API 密钥
API_KEY = os.environ.get("GROK_API_KEY") 
GROK_MODEL = "x-ai/grok-4.1-fast:free" 

app = Flask(__name__)
# 启用 CORS，允许所有来源访问，以解决跨域问题
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
        # 启用流式传输
        "stream": True 
    }

    try:
        # 发起请求时设置 stream=True，以便实时读取数据
        # 增加超时时间以防止 Grok 响应慢时导致连接中断
        response = requests.post(url, headers=headers, json=data, stream=True, timeout=180) 
        
        # 检查 API 状态码
        if response.status_code != 200:
            error_details = response.text
            print(f"API 调用返回非 200 状态码: {response.status_code}")
            print(f"详细错误信息: {error_details}")
            # 返回错误信息（非流式），前端会显示这个错误
            return f"❌ Grok API 调用失败，状态码 {response.status_code}。详情：{error_details}"


        # --- 生成器函数：实时处理和发送流数据 ---
        def generate():
            # 逐行读取 API 的流式响应
            for line in response.iter_lines():
                if line:
                    try:
                        decoded_line = line.decode('utf-8')
                    except UnicodeDecodeError:
                        # 忽略无法解码的行
                        continue
                        
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
                        except json.JSONDecodeError as e:
                            # 打印无法解析的 JSON，有助于调试
                            print(f"JSON 解析错误: {e}, 原始数据: {data_chunk}")
                            continue

            print("Stream finished.")
        
        # 关键：将生成器函数封装成 Flask Response，以 text/plain 格式流式返回
        return Response(generate(), mimetype='text/plain')
        
    except requests.exceptions.RequestException as e:
        # 网络连接或超时错误
        error_message = f"网络请求错误或超时: {e}"
        print(error_message)
        # 返回错误信息
        return error_message

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
        return Response("API Error: 请求体格式错误。", status=400, mimetype='text/plain')

    if not user_message:
        return Response("API Error: 缺少 'message' 字段。", status=400, mimetype='text/plain')

    # 关键：直接返回 ask_grok 的结果，它现在是流式响应（Response 对象）
    response_or_error = ask_grok(user_message)
    
    # 如果 ask_grok 返回的是字符串（意味着是错误信息）
    if isinstance(response_or_error, str):
         # 返回 500 错误状态，并把错误信息作为响应体
        return Response(response_or_error, status=500, mimetype='text/plain')
        
    # 否则，返回 Response 对象（流）
    return response_or_error

if __name__ == '__main__':
    print("Flask Grok API Server is starting...")
    app.run(debug=True, port=5000)
