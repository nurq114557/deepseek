import streamlit as st
from openai import OpenAI

st.title("我的专属 DeepSeek 助手")

client = OpenAI(
    api_key = st.secrets["DEEPSEEK_API_KEY"],  # 记得重新填入你的真实密钥
    base_url="https://api.deepseek.com"
)

# 写入系统提示词，强制它理解中文语境
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "system", "content": "你是会深度思考的AI助手。"}
    ]

# 渲染历史记录（隐藏掉系统提示词，只显示你和AI的对话）
for msg in st.session_state.messages:
    if msg["role"] != "system":
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

user_input = st.chat_input("请输入你的问题...")

if user_input:
    with st.chat_message("user"):
        st.markdown(user_input)
    
    st.session_state.messages.append({"role": "user", "content": user_input})

    with st.chat_message("assistant"):
        # 发送请求给服务器
        response = client.chat.completions.create(
            model="deepseek-reasoner", 
            messages=st.session_state.messages
        )
        
        # 提取思考过程 和 最终回答
        reasoning = response.choices[0].message.reasoning_content
        reply = response.choices[0].message.content
        
        # 1. 如果有思考过程，用一个折叠框把它展示出来
        if reasoning:
            with st.expander("🤔 点击查看思考过程"):
                st.markdown(reasoning)
                
        # 2. 显示最终回答
        st.markdown(reply)

        # 打印本次调用的 Token 消耗量（也就是你的扣费依据）
        st.caption(f"本次计费数据：{response.usage.total_tokens} Tokens")
        
    st.session_state.messages.append({"role": "assistant", "content": reply})