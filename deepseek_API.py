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

# ========== 侧边栏设置 ==========
with st.sidebar:
    st.title("⚙️ 设置")

    # API密钥配置
    api_key = st.text_input(
        "DeepSeek API密钥",
        type="password",
        value=st.secrets.get("DEEPSEEK_API_KEY", "") if hasattr(st, 'secrets') else "",
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
    temperature = st.slider("温度", 0.0, 2.0, 0.7, 0.1,
                          help="值越高回答越随机，值越低回答越确定")
    max_tokens = st.slider("最大生成长度", 100, 4096, 2048, 100)

    # 上下文管理
    st.subheader("上下文管理")
    max_history = st.number_input("最大对话轮数", 1, 50, 10,
                                 help="限制对话历史长度以控制token消耗")

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
def process_user_input(user_input: str):
    """处理用户输入的安全过滤"""
    # 基本的输入过滤
    if not user_input or user_input.strip() == "":
        return None

    # 防止超长输入
    if len(user_input) > 2000:
        st.warning("输入过长，请控制在2000字符以内")
        return None

    # 替换可能的危险字符
    safe_input = user_input.replace("<", "&lt;").replace(">", "&gt;")
    return safe_input

# 输入框
user_input = st.chat_input("请输入您的问题...")

if user_input:
    # 输入处理
    processed_input = process_user_input(user_input)
    if not processed_input:
        st.stop()

    # 显示用户消息
    with st.chat_message("user"):
        st.markdown(processed_input)

    # 添加到历史（限制历史长度）
    st.session_state.messages.append({"role": "user", "content": processed_input})

    # 上下文截断（防止token溢出）
    if len(st.session_state.messages) > max_history * 2:  # 乘以2因为包含user和assistant
        # 保留系统消息和最近对话
        st.session_state.messages = [
            st.session_state.messages[0]
        ] + st.session_state.messages[-(max_history * 2):]

    # 显示助手回复
与st.chat_message(“assistant"):
        message_placeholder = st.empty()
        message_placeholder.markdown("⏳ 思考中...")

        try:
            # 发送请求
            response = client.chat.completions.create(
                model=model_options[selected_model],
                messages=st.session_state.messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=False
            )

            # 提取响应
            reasoning = getattr(response.choices[0].message, 'reasoning_content', None)
            reply = response.choices[0].message.content

            # 如果有思考过程
如果推理:
                with st.expander("🧠 深度思考", expanded=False):
                    st.markdown(reasoning)

            # 显示回复
message_placeholder.减价(回复)

            # 显示token使用信息
Token_info = {
                "提示词": response.usage.prompt_tokens,
                "生成": response.usage.completion_tokens,
"总计": response.usage.total_tokens
            }
st.caption(f"Token用量: {token_info['总计']} (提示词: {token_info['提示词']}, 生成: {token_info['生成']})")

            # 保存到历史（包含思考过程）
助教_msg = {
"role": "assistant",
“content":回复,
“model": selected_model,
"tokens": token_info["总计"],
"timestamp": datetime.now().isoformat()
            }
如果推理:
                assistant_msg["reasoning"] = reasoning

            st.session_state.messages.append(assistant_msg)

        except Exception as e:
            error_msg = f"请求失败: {str(e)}"
            message_placeholder.error(error_msg)

            # 如果是token超限错误
            if "context length" in str(e).lower() or "token" in str(e).lower():
                st.info("💡 提示：对话历史过长，已自动清理较早的记录")
                # 清理部分历史
                st.session_state.messages = [
                    st.session_state.messages[0],
                    st.session_state.messages[-2],  # 用户上一条消息
                    {"role": "assistant", "content": "由于上下文长度限制，已清理较早对话历史。请继续提问。"}
                ]
                st.rerun()

# ========== 底部信息 ==========
st.divider()
Col1, col2, col3 = st.columns(3)
with col1:
{len([m 为 m 在 st.session_state.]如果m['role'] ！= '系统'])}“)
col2:
如果st.session_state。消息和len(st.session_state。留言)> 1：
Last_msg = st.session_state.消息[-1]
如果last_msg.get (" model"):
st.caption(f"🔧 当前模型: {last_msg['model']}")
col3:
. title （"；由DeepSeek api提供支持"；）
