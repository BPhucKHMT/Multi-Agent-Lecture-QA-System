
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

import streamlit as st
import time
import json
import re
import requests
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any
from src.shared.config import get_path

# ============ CONFIGURATION ============
CONVERSATIONS_DIR = get_path("saved_conversations_dir")
Path(CONVERSATIONS_DIR).mkdir(parents=True, exist_ok=True)

# ============ UTILITIES ============
def truncate_text(text, max_length=35):
    if len(text) > max_length:
        return text[:max_length] + "..."
    return text

def timestamp_to_seconds(timestamp: str) -> int:
    """Chuyển HH:MM:SS hoặc MM:SS sang seconds"""
    try:
        parts = list(map(int, timestamp.split(':')))
        if len(parts) == 3:
            return parts[0] * 3600 + parts[1] * 60 + parts[2]
        elif len(parts) == 2:
            return parts[0] * 60 + parts[1]
    except:
        pass
    return 0

def response_to_display_text(response) -> str:
    """Convert response thành plain text"""
    if isinstance(response, dict):
        text = response.get('text', '')
        clean_text = re.sub(r'\[(\d+)\]', r'[\1]', text)
        return clean_text
    elif isinstance(response, str):
        return response
    else:
        return str(response)

def render_response(response):
    """Universal renderer"""
    if isinstance(response, dict):
        response_type = response.get('type', 'unknown')
        text = response.get('text', '')
        video_urls = response.get('video_url', [])
        titles = response.get('title', [])
        start_timestamps = response.get('start_timestamp', [])
        end_timestamps = response.get('end_timestamp', [])
        confidences = response.get('confidence', [])
        
        if video_urls:
            def replace_citation(match):
                index = int(match.group(1))
                if index < len(video_urls):
                    url = video_urls[index]
                    title = titles[index] if index < len(titles) else f"Video {index}"
                    start = start_timestamps[index] if index < len(start_timestamps) else "00:00:00"
                    seconds = timestamp_to_seconds(start)
                    video_link = f"{url}&t={seconds}" if '?' in url else f"{url}?t={seconds}"
                    return f'<a href="{video_link}" target="_blank" style="color: #1E88E5; font-weight: bold; text-decoration: none; border-bottom: 1px dotted #1E88E5;" title="{title} - {start}">[{index}]</a>'
                return match.group(0)
            formatted_text = re.sub(r'\[(\d+)\]', replace_citation, text)
        else:
            formatted_text = text
        
        st.markdown(formatted_text, unsafe_allow_html=True)
        
        if video_urls and response_type == "rag":
            st.markdown("---")
            st.markdown("### 📺 Nguồn tham khảo:")
            for i, url in enumerate(video_urls):
                title = titles[i] if i < len(titles) else f"Video {i}"
                start = start_timestamps[i] if i < len(start_timestamps) else "00:00:00"
                end = end_timestamps[i] if i < len(end_timestamps) else start
                confidence = confidences[i] if i < len(confidences) else "unknown"
                seconds = timestamp_to_seconds(start)
                video_link = f"{url}&t={seconds}" if '?' in url else f"{url}?t={seconds}"
                conf_emoji = {'high': '🟢', 'medium': '🟡', 'low': '🟠', 'zero': '🔴'}.get(confidence, '⚪')
                st.markdown(f"**{i}.** {conf_emoji} [{title}]({video_link}) ⏱️ `{start}` → `{end}`")
    
    elif isinstance(response, str):
        st.markdown(response, unsafe_allow_html=True)
    else:
        st.error(f"⚠️ Unknown response format: {type(response)}")

# ============ LOCAL CONVERSATION FUNCTIONS ============
def load_all_conversations():
    """Load all conversations from session state (local only)"""
    return {}

def load_conversation_messages(convo_id: str) -> List[Dict]:
    """Load full message history for a conversation (local only)"""
    return st.session_state.conversations.get(convo_id, {}).get("messages", [])

def delete_conversation(convo_id: str):
    """Delete conversation from local session state only"""
    try:
        if convo_id in st.session_state.conversations:
            del st.session_state.conversations[convo_id]
        # Reset current ID nếu đang active
        if st.session_state.current_conversation_id == convo_id:
            remaining_convos = list(st.session_state.conversations.keys())
            if remaining_convos:
                st.session_state.current_conversation_id = remaining_convos[-1]
            else:
                create_new_conversation()
        return True
    except:
        return False

def reset_conversation(convo_id: str):
    """Reset conversation in local session state only"""
    try:
        st.session_state.conversations[convo_id] = {
            "title": "Cuộc trò chuyện mới",
            "messages": [{"role": "assistant", "content": "Bạn muốn hỏi gì hôm nay?"}],
            "created_at": datetime.now().isoformat()
        }
        return True
    except:
        return False

# ============ SESSION MANAGEMENT ============
import uuid
def create_new_conversation():
    """Tạo conversation mới (local only)"""
    try:
        convo_id = str(uuid.uuid4())
        st.session_state.conversations[convo_id] = {
            "title": "Cuộc trò chuyện mới",
            "messages": [{"role": "assistant", "content": "Bạn muốn hỏi gì hôm nay?"}],
            "created_at": datetime.now().isoformat()
        }
        st.session_state.current_conversation_id = convo_id
    except Exception as e:
        st.error(f"Error creating conversation: {e}")

def set_current_conversation(convo_id):
    """Switch conversation"""
    st.session_state.current_conversation_id = convo_id

# ============ SETUP PAGE ============
st.set_page_config(
    page_title="PUQ Q&A",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .stButton button {
        width: 100%;
    }
    .block-container {
        padding-top: 2rem;
    }
</style>
""", unsafe_allow_html=True)


st.title("🤖 PUQ Q&A")

# ============ INITIALIZE SESSION STATE ============
if "conversations" not in st.session_state:
    # Initialize empty conversations dict
    st.session_state.conversations = {}

if "current_conversation_id" not in st.session_state:
    st.session_state.current_conversation_id = None

if not st.session_state.conversations:
    create_new_conversation()

# ============ SIDEBAR ============
with st.sidebar:
    st.title("💬 Cuộc trò chuyện")

    if st.button("➕ Cuộc trò chuyện mới", use_container_width=True):
        create_new_conversation()
        st.rerun()

    st.divider()

    if "search_query" not in st.session_state:
        st.session_state["search_query"] = ""

    search_query = st.text_input(
        "🔍 Tìm kiếm",
        value=st.session_state["search_query"],
        placeholder="Nhập từ khóa..."
    )
    st.session_state["search_query"] = search_query

    st.subheader("Gần đây")

    convo_ids = list(st.session_state.conversations.keys())

    if search_query:
        filtered_ids = [
            cid for cid in convo_ids
            if search_query.lower() in st.session_state.conversations[cid]["title"].lower()
        ]
    else:
        filtered_ids = convo_ids

    st.markdown("""
    <style>
    .sidebar-row button {
        height: 38px !important;
        padding: 0 !important;
    }
    .icon-btn button {
        min-width: 38px !important;
        max-width: 38px !important;
    }
    </style>
    """, unsafe_allow_html=True)

    for convo_id in reversed(filtered_ids):
        convo = st.session_state.conversations[convo_id]
        title = convo["title"]
        is_active = convo_id == st.session_state.current_conversation_id

        col1, col2, col3 = st.columns([5, 3, 3], gap="small")

        with col1:
            st.markdown("<div class='sidebar-row'>", unsafe_allow_html=True)
            if st.button(
                title,
                key=f"select_{convo_id}",
                type="primary" if is_active else "secondary",
                use_container_width=True
            ):
                set_current_conversation(convo_id)
                st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

        with col2:
            st.markdown("<div class='icon-btn'>", unsafe_allow_html=True)
            if st.button("🗑️", key=f"delete_{convo_id}", use_container_width=True):
                if delete_conversation(convo_id):
                    st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

        with col3:
            st.markdown("<div class='icon-btn'>", unsafe_allow_html=True)
            if st.button("🔄", key=f"reset_{convo_id}", use_container_width=True):
                if reset_conversation(convo_id):
                    st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

# ============ MAIN CHAT AREA ============
current_id = st.session_state.current_conversation_id

if current_id and current_id in st.session_state.conversations:
    current_convo = st.session_state.conversations[current_id]
    # Messages are always in session state now
    messages = current_convo["messages"]
    
    # Display messages
    for message in messages:
        with st.chat_message(message["role"]):
            content = message["content"]
            if message["role"] == "assistant":
                render_response(content)
            else:
                st.markdown(content)
    
    # User input
    if prompt := st.chat_input("Nhắn tin..."):
        # Add user message
        messages.append({"role": "user", "content": prompt})
        
        # Update title if new conversation
        if current_convo["title"] == "Cuộc trò chuyện mới":
            current_convo["title"] = truncate_text(prompt)
        
        # Display user message
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # Prepare chat history
        chat_history = []
        for m in messages:
            content = m["content"]
            if isinstance(content, dict):
                content = response_to_display_text(content)
            chat_history.append({"role": m["role"], "content": content})
        # Call backend API for RAG response with streaming
        with st.chat_message("assistant"):
            placeholder = st.empty()
            full_text = ""
            final_metadata = {}
            placeholder.markdown("⏳ Đang gửi yêu cầu...")

            try:
                import requests
                import json
                with requests.post(
                    "http://localhost:8000/chat/stream",
                    json={
                        "conversation_id": current_id,
                        "messages": chat_history,
                        "user_message": prompt,
                    },
                    stream=True,
                    timeout=360,
                ) as stream_resp:
                    if stream_resp.status_code == 200:
                        placeholder.markdown("⏳ Server đang xử lý, vui lòng chờ...")
                        for raw_line in stream_resp.iter_lines():
                            if raw_line:
                                decoded = raw_line.decode("utf-8")
                                if decoded.startswith("data: ") and decoded != "data: [DONE]":
                                    try:
                                        data = json.loads(decoded[6:])
                                        if data.get("type") == "token":
                                            full_text += data.get("content", "")
                                            # Using markdown to show text typing out + cursor
                                            placeholder.markdown(full_text + " ▌")
                                        elif data.get("type") == "metadata":
                                            final_metadata = data.get("response", {})
                                            placeholder.markdown("✅ Đã nhận phản hồi, đang hiển thị...")
                                    except json.JSONDecodeError:
                                        pass

                        # Render again after stream is complete with the actual metadata
                        placeholder.empty()
                        if final_metadata:
                            render_response(final_metadata)
                            messages.append({"role": "assistant", "content": final_metadata})
                        else:
                            # Fallback if no metadata received
                            fallback_text = full_text or "⚠️ Không nhận được phản hồi hợp lệ từ server."
                            st.markdown(fallback_text)
                            messages.append({"role": "assistant", "content": {
                                "text": fallback_text, "type": "error",
                                "video_url": [], "title": [], "filename": [],
                                "start_timestamp": [], "end_timestamp": [], "confidence": []
                            }})

                        if current_convo["title"] == "Cuộc trò chuyện mới":
                            current_convo["title"] = truncate_text(prompt)
                    else:
                        error_msg = "⚠️ Không thể kết nối với server"
                        st.error(error_msg)
                        messages.append({"role": "assistant", "content": error_msg})

            except Exception as e:
                error_msg = f"⚠️ Có lỗi xảy ra: {str(e)}"
                st.error(error_msg)
                messages.append({"role": "assistant", "content": error_msg})
        st.rerun()

else:
    st.info("👈 Vui lòng chọn hoặc tạo cuộc trò chuyện từ thanh bên.")
