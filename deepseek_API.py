import streamlit as st
from openai import OpenAI
from datetime import datetime
import json

# ========== 页面配置 ==========
st.set_page_config(
    page_title="DeepSeek智能助手",
    page_icon="🤖",
    layout="wide"
)

# ========== 安全获取密钥 ==========
def get_default_api_key():
    try:
        return st.secrets.get("DEEPSEEK_API_KEY", "")
    except Exception:
        return ""

# ========== 侧边栏设置 ==========
with st.sidebar:
    st.title("⚙️ 设置")

    # API密钥配置
    api_key = st.text_input(
        "DeepSeek API密钥",
        type="password",
        value=get_default_api_key(),
        help="从DeepSeek官网获取API密钥"
    )

    # 模型选择
    model_options = {
        "DeepSeek-R1": "deepseek-reasoner",
        "DeepSeek-V3": "deepseek-chat",
        "DeepSeek-Coder": "deepseek-coder"
    }
    selected_model = st.selectbox(
        "选择模型",
        options=list(model_options.keys()),
        index=0
    )

    # 高级参数
    st.subheader("高级参数")
    temperature = st.slider("温度", 0.0, 2.0, 0.7, 0.1, help="值越高回答越随机，值越低回答越确定")
    max_tokens = st.slider("最大生成长度", 100, 4096, 2048, 100)

    # 上下文管理
    st.subheader("上下文管理")
    max_history = st.number_input("最大对话轮数", 1, 50, 10, help="限制对话历史长度以控制token消耗")

    # 控制按钮
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🔄 清空对话", use_container_width=True):
            st.session_state.messages = [
                {"role": "system", "content": "你是会深度思考的AI助手。"}
            ]
            st.rerun()

    with col2:
        if st.button("💾 导出对话", use_container_width=True):
            if "messages" in st.session_state:
                export_data = {
                    "export_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "model": selected_model,
                    "messages": st.session_state.messages[1:]  # 排除系统消息
                }
                st.download_button(
                    label="下载JSON文件",
                    data=json.dumps(export_data, ensure_ascii=False, indent=2),
                    file_name=f"deepseek_chat_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                    mime="application/json"
                )

# ========== 主页面 ==========
st.title("🤖 DeepSeek智能助手")
st.caption("一款基于DeepSeek API的智能对话助手")

# 初始化客户端
if not api_key:
    st.warning("⚠️ 请在侧边栏输入API密钥")
    st.stop()

try:
    client = OpenAI(
        api_key=api_key,
        base_url="https://api.deepseek.com"
    )
except Exception as e:
    st.error(f"客户端初始化失败: {str(e)}")
    st.stop()

# ========== 初始化对话历史 ==========
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "system", "content": "你是会深度思考的AI助手。"}
    ]

# ========== 显示对话历史 ==========
for i, msg in enumerate(st.session_state.messages):
    if msg["role"] != "system":
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            # 显示思考过程（如果有）
            if msg.get("reasoning"):
                with st.expander("🤔 思考过程", expanded=False):
                    st.markdown(msg["reasoning"])

# ========== 处理用户输入 ==========
def process_user_input(user_input_text: str):
    if not user_input_text or user_input_text.strip() == "":
        return None
    if len(user_input_text) > 2000:
        st.warning("输入过长，请控制在2000字符以内")
        return None
    return user_input_text.replace("<", "&lt;").replace(">", "&gt;")

user_input = st.chat_input("请输入您的问题...")

if user_input:
    processed_input = process_user_input(user_input)
    if not processed_input:
        st.stop()

    with st.chat_message("user"):
        st.markdown(processed_input)

    st.session_state.messages.append({"role": "user", "content": processed_input})

    if len(st.session_state.messages) > max_history * 2:
        st.session_state.messages = [st.session_state.messages[0]] + st.session_state.messages[-(max_history * 2):]

    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        message_placeholder.markdown("⏳ 思考中...")

        try:
            # 【关键修复】：剥离无用字段，只传递 role 和 content 给 API
            api_messages = [{"role": m["role"], "content": m["content"]} for m in st.session_state.messages]
            
            response = client.chat.completions.create(
                model=model_options[selected_model],
                messages=api_messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=False
            )

            reasoning = getattr(response.choices[0].message, 'reasoning_content', None)
            reply = response.choices[0].message.content

            if reasoning:
                with st.expander("🧠 深度思考", expanded=False):
                    st.markdown(reasoning)

            message_placeholder.markdown(reply)

            token_info = {
                "提示词": response.usage.prompt_tokens,
                "生成": response.usage.completion_tokens,
                "总计": response.usage.total_tokens
            }
            st.caption(f"Token用量: {token_info['总计']} (提示词: {token_info['提示词']}, 生成: {token_info['生成']})")

            # 存入完整的本地记录（包含UI所需的额外字段，这些字段在下一次请求时会被上方清洗掉）
            assistant_msg = {
                "role": "assistant", 
                "content": reply,
                "model": selected_model,
                "tokens": token_info["总计"],
                "timestamp": datetime.now().isoformat()
            }
            if reasoning:
                assistant_msg["reasoning"] = reasoning

            st.session_state.messages.append(assistant_msg)

        except Exception as e:
            error_msg = f"请求失败: {str(e)}"
            message_placeholder.error(error_msg)

            if "context length" in str(e).lower() or "token" in str(e).lower():
                st.info("💡 提示：对话历史过长，已自动清理较早的记录")
                st.session_state.messages = [
                    st.session_state.messages[0],
                    st.session_state.messages[-2],
                    {"role": "assistant", "content": "由于上下文长度限制，已清理较早对话历史。请继续提问。"}
                ]
                st.rerun()

# ========== 底部信息 ==========
st.divider()
col1, col2, col3 = st.columns(3)
with col1:
    st.caption(f"💬 对话轮数: {len([m for m in st.session_state.messages if m['role'] != 'system'])}")
with col2:
    if st.session_state.messages and len(st.session_state.messages) > 1:
        last_msg = st.session_state.messages[-1]
        if last_msg.get("model"):
            st.caption(f"🔧 当前模型: {last_msg['model']}")
with col3:
    st.caption("Powered by DeepSeek API")
