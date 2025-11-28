import streamlit as st
import google.generativeai as genai
from PIL import Image, ExifTags
import time
from datetime import datetime
import warnings
import random
import os
import logging
import io
import base64

# ================= 0. 核心配置 & 强力消音 =================
warnings.filterwarnings("ignore")
os.environ['STREAMLIT_logger_level'] = 'error'
logging.getLogger('streamlit').setLevel(logging.ERROR)

st.set_page_config(
    page_title="智影 | AI 影像顾问", 
    page_icon="🌿", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# ================= 1. 状态初始化 (包含深色模式) =================
def init_session_state():
    defaults = {
        'logged_in': False,
        'user_phone': None,
        'expire_date': None,
        'history': [],
        'favorites': [],
        'font_size': 16,
        'dark_mode': False,       # 👈 找回了深色模式状态
        'current_report': None,
        'current_image': None,
        'current_req': None
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

init_session_state()

# ================= 2. 动态 CSS (换肤引擎) =================
def inject_custom_css():
    # 根据状态定义颜色变量
    if st.session_state.dark_mode:
        # 深色主题
        main_bg = "#121212"
        text_col = "#E0E0E0"
        card_bg = "#1E1E1E"
        sidebar_bg = "#262626"
        border_col = "#333"
        shadow_col = "rgba(255,255,255,0.05)"
    else:
        # 浅色主题
        main_bg = "#FFFFFF"
        text_col = "#333333"
        card_bg = "#f8f9fa"
        sidebar_bg = "#F0F2F6"
        border_col = "#e0e0e0"
        shadow_col = "rgba(0,0,0,0.05)"

    font_px = st.session_state.font_size

    st.markdown(f"""
    <style>
    /* 全局去噪 */
    #MainMenu {{visibility: hidden;}}
    footer {{visibility: hidden;}}
    header {{visibility: hidden;}}
    
    /* 1. 全局背景与文字 */
    .stApp {{
        background-color: {main_bg};
        color: {text_col};
        transition: all 0.3s ease;
    }}
    
    /* 2. 侧边栏背景 */
    section[data-testid="stSidebar"] {{
        background-color: {sidebar_bg};
        display: block !important;
    }}
    
    /* 3. 结果卡片美化 */
    .result-card {{
        background-color: {card_bg};
        color: {text_col};
        border-left: 5px solid #4CAF50;
        padding: 25px;
        border-radius: 10px;
        margin-top: 15px;
        margin-bottom: 20px;
        box-shadow: 0 4px 10px {shadow_col};
        border: 1px solid {border_col};
    }}
    
    /* 4. 字体大小控制 (动态) */
    .stMarkdown p, .stMarkdown li, .stMarkdown div {{
        font-size: {font_px}px !important;
        line-height: 1.7 !important;
    }}
    
    /* 5. 手机端顶部优化 */
    .block-container {{
        padding-top: 1rem !important;
        padding-bottom: 1rem !important;
    }}
    
    /* 6. 侧边栏按钮颜色强制修正 */
    button[kind="header"] {{
        color: #4CAF50 !important;
    }}
    </style>
    """, unsafe_allow_html=True)

# 立即注入样式
inject_custom_css()

# ================= 3. 工具函数库 =================
def img_to_base64(image):
    try:
        buffered = io.BytesIO()
        image.save(buffered, format="JPEG", quality=50)
        return base64.b64encode(buffered.getvalue()).decode()
    except: return ""

def configure_random_key():
    try:
        keys = st.secrets["API_KEYS"]
        key_list = [keys] if isinstance(keys, str) else keys
        current_key = random.choice(key_list)
        genai.configure(api_key=current_key)
        return True
    except Exception as e:
        st.error(f"⚠️ 系统配置错误: {e}")
        return False

def get_exif_data(image):
    exif_data = {}
    try:
        info = image._getexif()
        if info:
            for tag, value in info.items():
                decoded = ExifTags.TAGS.get(tag, tag)
                if decoded in ['Make', 'Model', 'ISO', 'FNumber', 'ExposureTime']:
                    exif_data[decoded] = str(value)
    except: pass
    return exif_data

def create_html_report(text, user_req, img_base64):
    img_tag = f'<img src="data:image/jpeg;base64,{img_base64}" style="max-width:100%; border-radius:10px; margin-bottom:20px;">' if img_base64 else ""
    return f"""
    <html>
    <head><meta charset="utf-8"></head>
    <body style="font-family: sans-serif; padding: 20px; line-height: 1.6;">
    <h2 style='color:#2E7D32'>🌿 智影 | 专业影像分析报告</h2>
    <p style="color:gray; font-size:12px;">生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}</p>
    {img_tag}
    <div style="background:#f0f2f6; padding:15px; border-radius:5px; margin-bottom:20px;">
        <b>用户备注:</b> {user_req if user_req else '无'}
    </div>
    <hr>
    {text.replace(chr(10), '<br>').replace('###', '<h3>').replace('# ', '<h1>').replace('**', '<b>')}
    </body></html>
    """

# ================= 4. 登录页 =================
def show_login_page():
    col_poster, col_login = st.columns([1, 1])
    with col_poster:
        st.image("https://images.unsplash.com/photo-1472214103451-9374bd1c798e?q=80&w=1000&auto=format&fit=crop", 
                 use_container_width=True)

    with col_login:
        st.title("🌿 智影")
        st.markdown("##### 您的 24小时 AI 摄影私教")
        st.info("✨ **一键评分** | 📊 **参数直出** | 🎓 **大师指导**")
        
        with st.container(border=True):
            st.subheader("🔐 会员登录")
            phone_input = st.text_input("手机号码", placeholder="请输入手机号", max_chars=11)
            code_input = st.text_input("激活码 / Key", placeholder="请输入专属 Key", type="password")
            
            if st.button("立即登录", type="primary", use_container_width=True):
                try:
                    valid_accounts = st.secrets["VALID_ACCOUNTS"]
                    login_success = False
                    expire_date_str = ""
                    for account_str in valid_accounts:
                        parts = account_str.split(":")
                        if len(parts) == 3 and phone_input == parts[0].strip() and code_input == parts[1].strip():
                            exp_date = datetime.strptime(parts[2].strip(), "%Y-%m-%d")
                            if datetime.now() > exp_date:
                                st.error(f"❌ 会员已于 {parts[2]} 到期")
                                return
                            login_success = True
                            expire_date_str = parts[2]
                            break
                    
                    if login_success:
                        st.session_state.logged_in = True
                        st.session_state.user_phone = phone_input
                        st.session_state.expire_date = expire_date_str
                        st.session_state.history = []
                        st.session_state.favorites = []
                        print(f"[MONITOR] LOGIN SUCCESS | User: {phone_input}")
                        st.rerun()
                    else:
                        st.error("账号或激活码错误")
                except Exception as e:
                    st.error("配置错误")

        st.caption("💎 获取激活码请联系微信：**BayernGomez**")
        with st.expander("📲 安装教程"):
            st.markdown("iPhone: Safari分享 -> 添加到主屏幕\nAndroid: Chrome菜单 -> 添加到主屏幕")

# ================= 5. 主程序 (完整版) =================
def show_main_app():
    if not configure_random_key():
        st.stop()

    with st.sidebar:
        st.title("🌿 用户中心")
        st.caption(f"用户: {st.session_state.user_phone} | 有效期: {st.session_state.expire_date}")
        
        st.markdown("---")
        mode_select = st.radio("模式选择:", ["📷 日常快评", "🧐 专业艺术"], index=0)

        st.markdown("---")
        # 历史记录
        with st.expander("🕒 历史记录", expanded=False):
            if not st.session_state.history:
                st.caption("暂无记录")
            else:
                for idx, item in enumerate(reversed(st.session_state.history)):
                    with st.popover(f"📄 {item['time']} - {item['mode']}"):
                        if item.get('img_base64'):
                            st.markdown(f'<img src="data:image/jpeg;base64,{item["img_base64"]}" width="100%" style="border-radius:5px;">', unsafe_allow_html=True)
                        st.markdown(item['content'])

        # 收藏夹
        with st.expander("❤️ 我的收藏", expanded=False):
            if not st.session_state.favorites:
                st.caption("暂无收藏")
            else:
                for idx, item in enumerate(st.session_state.favorites):
                    with st.popover(f"⭐ 收藏 #{idx+1}"):
                        if item.get('img_base64'):
                            st.markdown(f'<img src="data:image/jpeg;base64,{item["img_base64"]}" width="100%" style="border-radius:5px;">', unsafe_allow_html=True)
                        st.markdown(item['content'])

        st.markdown("---")
        # === ⚙️ 个性化设置 (功能已找回！) ===
        with st.expander("🛠️ 个性化设置", expanded=True):
            # 1. 字体大小
            new_size = st.slider("Aa 字体大小", 14, 24, st.session_state.font_size)
            if new_size != st.session_state.font_size:
                st.session_state.font_size = new_size
                st.rerun()
            
            # 2. 深色模式 (它回来了！)
            new_dark = st.toggle("🌙 深色模式", value=st.session_state.dark_mode)
            if new_dark != st.session_state.dark_mode:
                st.session_state.dark_mode = new_dark
                st.rerun() # 立即刷新应用 CSS
                
            # 3. EXIF
            show_exif_info = st.checkbox("显示参数 (EXIF)", value=True)

        if st.button("退出登录", use_container_width=True):
            st.session_state.logged_in = False
            st.rerun()

    # --- 提示词系统 ---
    if "日常" in mode_select:
        real_model = "gemini-2.0-flash-lite-preview-02-05"
        active_prompt = """你是一位亲切的摄影博主“智影”。
请严格按照 Markdown 格式输出，标题与内容之间空一行。
# 🌟 综合评分: {分数}/10

### 📝 影像笔记
> {点评}

### 🎨 手机修图参数表 (Wake/iPhone)
| 参数 | 数值 | 目的 |
| :--- | :--- | :--- |
| ... | ... | ... |

### 📸 随手拍建议
...

---
**🌿 智影寄语:** {金句}"""
        status_msg = "✨ 正在生成手机修图方案..."
    else:
        real_model = "gemini-2.5-flash"
        active_prompt = """你是一位视觉总监“智影”。
请严格按照 Markdown 格式输出，标题与内容之间空一行。
# 🏆 艺术总评: {分数}/10

### 👁️ 视觉深度解析
...

### 🎨 商业后期面板 (Lightroom/C1)
| 模块 | 参数 | 建议 |
| :--- | :--- | :--- |
| ... | ... | ... |

### 🎓 大师进阶课
...

---
**🌿 智影寄语:** {哲理}"""
        status_msg = "🧠 正在进行商业级光影分析..."

    # --- 主界面 ---
    st.title("🌿 智影 | 影像私教")
    
    # 顶部 Tab 切换
    tab1, tab2 = st.tabs(["📂 上传照片", "📷 现场拍摄"])
    
    with tab1:
        f = st.file_uploader("支持 JPG/PNG", type=["jpg","png","webp"], key="up_file")
        if f: 
            st.session_state.current_image = Image.open(f).convert('RGB')
            
    with tab2:
        c = st.camera_input("点击拍摄", key="cam_file")
        if c: 
            st.session_state.current_image = Image.open(c).convert('RGB')

    # 清空重置按钮
    if st.button("🗑️ 清空重置 / 换张图", use_container_width=True):
        st.session_state.current_image = None
        st.session_state.current_report = None
        st.rerun()

    # --- 结果展示区 ---
    if st.session_state.current_image:
        st.divider()
        c1, c2 = st.columns([1, 1.2])
        
        with c1:
            st.image(st.session_state.current_image, caption="待分析影像", use_container_width=True)
            if show_exif_info:
                exif = get_exif_data(st.session_state.current_image)
                if exif:
                    with st.expander("📷 拍摄参数"): st.json(exif)
        
        with c2:
            if not st.session_state.current_report:
                user_req = st.text_input("备注 (可选):", placeholder="例如：想修出日系感...")
                
                if st.button("🚀 开始评估", type="primary", use_container_width=True):
                    with st.status(status_msg, expanded=True) as s:
                        print(f"[MONITOR] ACTION | User: {st.session_state.user_phone} | Mode: {mode_select}")
                        
                        generation_config = genai.types.GenerationConfig(temperature=0.1)
                        model = genai.GenerativeModel(real_model, system_instruction=active_prompt)
                        
                        msg = "分析此图。"
                        if user_req: msg += f" 备注：{user_req}"
                        
                        response = model.generate_content([msg, st.session_state.current_image], generation_config=generation_config)
                        
                        st.session_state.current_report = response.text
                        st.session_state.current_req = user_req
                        s.update(label="✅ 分析完成", state="complete", expanded=False)
                        st.rerun()
            
            # 显示报告
            if st.session_state.current_report:
                # 这里的 class="result-card" 会根据上面的 CSS 自动变色（深/浅）
                st.markdown(f'<div class="result-card">{st.session_state.current_report}</div>', unsafe_allow_html=True)
                
                btn_c1, btn_c2 = st.columns(2)
                with btn_c1:
                    img_b64 = img_to_base64(st.session_state.current_image)
                    html = create_html_report(st.session_state.current_report, st.session_state.get('current_req', ''), img_b64)
                    st.download_button("📥 下载报告", html, file_name="智影报告.html", mime="text/html", use_container_width=True)
                
                with btn_c2:
                    if st.button("❤️ 加入收藏", use_container_width=True):
                        img_b64 = img_to_base64(st.session_state.current_image)
                        record = {
                            "time": datetime.now().strftime("%H:%M"),
                            "mode": mode_select,
                            "content": st.session_state.current_report,
                            "img_base64": img_b64
                        }
                        st.session_state.favorites.append(record)
                        st.session_state.history.append(record)
                        if len(st.session_state.history) > 5: st.session_state.history.pop(0)
                        st.toast("已收藏！", icon="⭐")

# ================= 6. 入口 =================
if __name__ == "__main__":
    if st.session_state.logged_in:
        show_main_app()
    else:
        show_login_page()