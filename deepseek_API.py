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

    # ========== 显示助手回复（关键升级：启用流式传输） ==========
    with st.chat_message("assistant"):
        # 【关键修改】：创建占位符以实现流式输出

        # 1. 用于打字机效果内容的占位符（用户目前看到“🤔 思考中...”的地方）
        content_placeholder = st.empty()
        # 2. 用于流式显示思考过程的占位符，默认展开
        streaming_reasoning_placeholder = st.empty()
        
        full_content = ""      # 存储完整的回复内容
        full_reasoning = ""    # 存储完整的思考过程
        final_usage = None     # 存储最终的 token 使用情况
        
        # 显示初始状态
        content_placeholder.markdown("⏳ 正在建立连接...")

        try:
            # 清洗API消息（只传递 role 和 content，保持不变）
            api_messages = [{"role": m["role"], "content": m["content"]} for m in st.session_state.messages]
            
            # 【关键修改】：将 stream 参数设为 True
            response_stream = client.chat.completions.create(
                model=model_options[selected_model],
                messages=api_messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True  # 启用流式传输
            )

            # 遍历响应流
            for chunk in response_stream:
                # 获取推理内容（Reasoning Content - R1特有）
                reasoning_chunk = getattr(chunk.choices[0].delta, 'reasoning_content', None)
                # 获取正式回复内容
                content_chunk = getattr(chunk.choices[0].delta, 'content', None)
                
                # 捕获 Token 使用情况（通常在最后一个块中）
                usage_chunk = getattr(chunk, 'usage', None)
                if usage_chunk:
                    final_usage = usage_chunk
                
                # 1. 处理推理内容流（对于R1模型）
                if reasoning_chunk:
                    # R1模式下，一旦开始输出思考，移除内容占位符，保持页面整洁
                    content_placeholder.empty()
                    full_reasoning += reasoning_chunk
                    with streaming_reasoning_placeholder.expander("🧠 深度思考中...", expanded=True):
                        st.markdown(full_reasoning + "▌") # 添加光标

                # 2. 处理正式内容流
                if content_chunk:
                    # 内容开始生成，移除临时的流式思考占位符，避免干扰
                    streaming_reasoning_placeholder.empty()
                    
                    full_content += content_chunk
                    # 使用打字机效果更新内容区域
                    content_placeholder.markdown(full_content + "▌")

            # ========== 生成结束后的最终渲染 ==========
            
            # 移除内容的光标
            content_placeholder.markdown(full_content)
            
            # 处理 R1 的思考过程：将其从临时的流式占位符移入最终折叠的可扩展器中
            if full_reasoning:
                # 确保临时思考区域已清空
                streaming_reasoning_placeholder.empty()
                # 在最终位置放置一个折叠的可扩展器，保持界面整洁
                with st.expander("🤔 深度思考（点击展开）", expanded=False):
                    st.markdown(full_reasoning)

            # 处理 Token 用量信息：流式传输后从最终响应中捕获
            if final_usage:
                token_info = {
                    "提示词": final_usage.prompt_tokens,
                    "生成": final_usage.completion_tokens,
                    "总计": final_usage.total_tokens
                }
                st.caption(f"Token用量: {token_info['总计']} (提示词: {token_info['提示词']}, 生成: {token_info['生成']})")

            # 保存到历史（包含完整的回复、思考过程和 token 信息）
            assistant_msg = {
                "role": "assistant", 
                "content": full_content,
                "model": selected_model,
                "tokens": final_usage.total_tokens if final_usage else None,
                "timestamp": datetime.now().isoformat()
            }
            if full_reasoning:
                assistant_msg["reasoning"] = full_reasoning

            st.session_state.messages.append(assistant_msg)

        except Exception as e:
            error_msg = f"请求失败: {str(e)}"
            content_placeholder.error(error_msg)

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
