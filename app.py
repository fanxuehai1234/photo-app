import streamlit as st
import google.generativeai as genai
from PIL import Image, ExifTags
import time
from datetime import datetime
import warnings
import random
import os
import io
import base64
import logging
import sys
import json
import re

# ================= 0. 核心配置 =================
warnings.filterwarnings("ignore")
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# SVG 图标
LEAF_ICON = "data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCAyNCAyNCIgZmlsbD0iIzRDQUY1MCI+PHBhdGggZD0iTTE3LDhDOCwxMCw1LjksMTYuMTcsMy44MiwyMS4zNEw1LjcxLDIybDEtMi4zQTQuNDksNC40OSwwLDAsMCw4LDIwQzE5LDIwLDIyLDMsMjIsMywyMSw1LDE0LDUuMjUsOSw2LjI1UzIsMTEuNSwyLDEzLjVhNi4yMiw2LjIyLDAsMCwwLDEuNzUsMy43NUM3LDgsMTcsOCwxNyw4WiIvPjwvc3ZnPg=="

st.set_page_config(
    page_title="智影 | AI 影像顾问", 
    page_icon="🌿", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# ================= 1. CSS 美化 =================
st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    div[class^="viewerBadge"] {display: none !important;} 
    
    .block-container {
        padding-top: 1rem !important;
        padding-bottom: 3rem !important;
    }
    
    section[data-testid="stSidebar"] {
        display: block;
    }
    
    .result-card {
        background-color: #f8f9fa;
        border-left: 5px solid #4CAF50;
        padding: 20px;
        border-radius: 8px;
        margin-top: 10px;
        margin-bottom: 20px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05);
    }
    
    .stButton>button {
        font-weight: bold;
        border-radius: 8px;
    }
    
    .trial-banner {
        background-color: #FFF3CD;
        color: #856404;
        padding: 10px;
        border-radius: 5px;
        text-align: center;
        margin-bottom: 15px;
        border: 1px solid #FFEEBA;
    }
    </style>
    """, unsafe_allow_html=True)

# ================= 2. 数据与逻辑引擎 =================

# --- A. 手机号正则校验 ---
def is_valid_phone(phone):
    pattern = r"^1[3-9]\d{9}$"
    return bool(re.match(pattern, phone))

# --- B. 游客数据管理 ---
GUEST_FILE = "guest_usage.json"
MAX_GUEST_USAGE = 3

def get_guest_usage(phone):
    if not os.path.exists(GUEST_FILE): return 0
    try:
        with open(GUEST_FILE, 'r') as f:
            data = json.load(f)
            return data.get(phone, 0)
    except: return 0

def save_guest_usage(phone):
    data = {}
    if os.path.exists(GUEST_FILE):
        try:
            with open(GUEST_FILE, 'r') as f:
                data = json.load(f)
        except: pass
    
    current = data.get(phone, 0)
    data[phone] = current + 1
    
    with open(GUEST_FILE, 'w') as f:
        json.dump(data, f)
    return data[phone]

# --- C. 智能 Key 管理 ---
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

# --- D. EXIF ---
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

# --- E. 报告生成 ---
def create_html_report(text, user_req, img_base64):
    img_tag = f'<img src="data:image/jpeg;base64,{img_base64}" style="max-width:100%; border-radius:10px; margin-bottom:20px;">' if img_base64 else ""
    return f"""
    <html><body>
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

def img_to_base64(image):
    try:
        buffered = io.BytesIO()
        image.save(buffered, format="JPEG", quality=50)
        return base64.b64encode(buffered.getvalue()).decode()
    except: return ""

# ================= 3. 状态初始化 =================
def init_session_state():
    defaults = {
        'logged_in': False,
        'user_phone': None,
        'user_role': 'guest',
        'expire_date': None,
        'history': [],
        'favorites': [],
        'font_size': 16,
        'dark_mode': False,
        'current_report': None,
        'processing': False
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

init_session_state()

def clear_camera():
    if 'cam_file' in st.session_state: del st.session_state['cam_file']
    st.session_state.current_report = None

def clear_upload():
    if 'up_file' in st.session_state: del st.session_state['up_file']
    st.session_state.current_report = None

def reset_all():
    if 'cam_file' in st.session_state: del st.session_state['cam_file']
    if 'up_file' in st.session_state: del st.session_state['up_file']
    st.session_state.current_report = None

# ================= 4. 登录页 (修复版：恢复双栏教程) =================
def show_login_page():
    col_poster, col_login = st.columns([1.2, 1])
    
    with col_poster:
        st.image("https://images.unsplash.com/photo-1516035069371-29a1b244cc32?q=80&w=1000&auto=format&fit=crop", 
                 use_container_width=True)
        st.markdown('<div style="text-align:center; color:#888; margin-top:10px; font-style:italic;">“ 光影之处，皆是生活 ”</div>', unsafe_allow_html=True)

    with col_login:
        st.markdown("<br>", unsafe_allow_html=True)
        
        st.markdown(f"""
        <div style="display:flex; align-items:center; margin-bottom:20px;">
            <img src="{LEAF_ICON}" style="width:50px; height:50px; margin-right:15px;">
            <h1 style="margin:0;">智影</h1>
        </div>
        """, unsafe_allow_html=True)
            
        st.markdown("#### 您的 24小时 AI 摄影私教")
        
        login_tab1, login_tab2 = st.tabs(["💎 会员登录", "🎁 游客试用"])
        
        # --- 会员登录 ---
        with login_tab1:
            with st.container(border=True):
                phone_input = st.text_input("手机号码", placeholder="请输入注册手机号", max_chars=11, key="vip_phone")
                code_input = st.text_input("激活码", placeholder="请输入专属 Key", type="password", key="vip_code")
                
                if st.button("会员登录", type="primary", use_container_width=True):
                    if not is_valid_phone(phone_input):
                        st.error("请输入正确的 11 位手机号码")
                    else:
                        try:
                            valid_accounts = st.secrets["VALID_ACCOUNTS"]
                            login_success = False
                            expire_date_str = ""
                            for account_str in valid_accounts:
                                parts = account_str.split(":")
                                if len(parts) == 3 and phone_input == parts[0].strip() and code_input == parts[1].strip():
                                    exp_date = datetime.strptime(parts[2].strip(), "%Y-%m-%d")
                                    if datetime.now() > exp_date:
                                        st.error(f"❌ 您的服务已于 {parts[2]} 到期")
                                        st.stop()
                                    login_success = True
                                    expire_date_str = parts[2]
                                    break
                            
                            if login_success:
                                st.session_state.logged_in = True
                                st.session_state.user_phone = phone_input
                                st.session_state.user_role = 'vip'
                                st.session_state.expire_date = expire_date_str
                                reset_all()
                                st.session_state.history = []
                                st.session_state.favorites = []
                                logger.info(f"⭐⭐⭐ [MONITOR] VIP LOGIN | User: {phone_input}")
                                st.rerun()
                            else:
                                st.error("账号或激活码错误")
                        except:
                            st.error("系统维护中")

        # --- 游客登录 ---
        with login_tab2:
            with st.container(border=True):
                st.info(f"🎁 新用户免费试用 {MAX_GUEST_USAGE} 次")
                guest_phone = st.text_input("手机号码", placeholder="请输入手机号", max_chars=11, key="guest_phone")
                
                if st.button("开始试用", use_container_width=True):
                    if not is_valid_phone(guest_phone):
                        st.error("请输入有效的 11 位手机号码")
                    else:
                        used_count = get_guest_usage(guest_phone)
                        if used_count >= MAX_GUEST_USAGE:
                            st.error("❌ 试用次数已用完")
                            st.warning("请联系微信 **BayernGomez28** 购买正式会员。")
                        else:
                            save_guest_usage(guest_phone) # 立即扣费防止刷
                            st.session_state.logged_in = True
                            st.session_state.user_phone = guest_phone
                            st.session_state.user_role = 'guest'
                            st.session_state.expire_date = "试用期"
                            reset_all()
                            st.session_state.history = []
                            st.session_state.favorites = []
                            logger.info(f"⭐⭐⭐ [MONITOR] GUEST LOGIN | User: {guest_phone}")
                            st.rerun()

        st.caption("💎 购买会员请联系微信：**BayernGomez28**")
        
        # 🟢 修复：这里恢复了双栏布局
        with st.expander("📲 安装教程 (iPhone / Android)"):
            c1, c2 = st.columns(2)
            with c1:
                st.markdown("**🍎 iPhone / iPad**")
                st.markdown("1. 使用 Safari 打开")
                st.markdown("2. 点击底部 [分享] 图标")
                st.markdown("3. 选择 [添加到主屏幕]")
            with c2:
                st.markdown("**🤖 Android 安卓**")
                st.markdown("1. 推荐 Chrome / Edge")
                st.markdown("2. 点击右上角菜单")
                st.markdown("3. 选择 [添加到主屏幕]")

# ================= 5. 主程序 =================
def show_main_app():
    if not configure_random_key():
        st.stop()

    if st.session_state.dark_mode:
        st.markdown("""<style>
        .stApp {background-color: #121212; color: #E0E0E0;}
        .result-card {background-color: #1E1E1E; color: #E0E0E0;}
        section[data-testid="stSidebar"] {background-color: #1E1E1E;}
        [data-baseweb="input"] {background-color: #262626; color: white;}
        .logo-text {color: #E0E0E0 !important;}
        </style>""", unsafe_allow_html=True)

    with st.sidebar:
        st.markdown(f"""
        <div class="logo-header" style="display:flex; align-items:center; margin-bottom:10px;">
            <img src="{LEAF_ICON}" style="width:30px; height:30px; margin-right:10px;">
            <h3 style="margin:0; font-size:1.2rem;">用户中心</h3>
        </div>
        """, unsafe_allow_html=True)
        
        if st.session_state.user_role == 'vip':
            st.success(f"💎 正式会员: {st.session_state.user_phone}")
            st.caption(f"有效期: {st.session_state.expire_date}")
        else:
            used = get_guest_usage(st.session_state.user_phone)
            remain = MAX_GUEST_USAGE - used
            st.warning(f"🎁 试用访客: {st.session_state.user_phone}")
            st.progress(used/MAX_GUEST_USAGE, text=f"剩余次数: {remain}/{MAX_GUEST_USAGE}")
        
        st.markdown("---")
        mode_select = st.radio("模式选择:", ["📷 日常快评", "🧐 专业艺术"], index=0)

        st.markdown("---")
        with st.expander("🕒 历史记录", expanded=False):
            if not st.session_state.history:
                st.caption("暂无记录")
            else:
                for idx, item in enumerate(reversed(st.session_state.history)):
                    with st.popover(f"📄 {item['time']} - {item['mode']}"):
                        if item.get('img_base64'):
                            st.markdown(f'<img src="data:image/jpeg;base64,{item["img_base64"]}" width="100%">', unsafe_allow_html=True)
                        st.markdown(item['content'])

        with st.expander("❤️ 我的收藏", expanded=False):
            if not st.session_state.favorites:
                st.caption("暂无收藏")
            else:
                for idx, item in enumerate(st.session_state.favorites):
                    with st.popover(f"⭐ 收藏 #{idx+1}"):
                        if item.get('img_base64'):
                            st.markdown(f'<img src="data:image/jpeg;base64,{item["img_base64"]}" width="100%">', unsafe_allow_html=True)
                        st.markdown(item['content'])

        st.markdown("---")
        with st.expander("🛠️ 设置", expanded=True):
            font_size = st.slider("字体大小", 14, 24, st.session_state.font_size)
            if font_size != st.session_state.font_size:
                st.session_state.font_size = font_size
                st.rerun()
            
            new_dark = st.toggle("🌙 深色模式", value=st.session_state.dark_mode)
            if new_dark != st.session_state.dark_mode:
                st.session_state.dark_mode = new_dark
                st.rerun()
                
            show_exif_info = st.checkbox("显示参数 (EXIF)", value=True)

        if st.button("退出登录", use_container_width=True):
            st.session_state.logged_in = False
            reset_all()
            st.rerun()
            
        st.markdown("---")
        st.caption("Ver: V35.0 Final")

    st.markdown(f"<style>.stMarkdown p, .stMarkdown li {{font-size: {font_size}px !important; line-height: 1.6;}}</style>", unsafe_allow_html=True)

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
        banner_text = "日常记录 | 适用：朋友圈、手机摄影、快速出片"
        banner_bg = "#e8f5e9" if not st.session_state.dark_mode else "#1b5e20"
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
        banner_text = "专业创作 | 适用：单反微单、商业修图、作品集"
        banner_bg = "#e3f2fd" if not st.session_state.dark_mode else "#0d47a1"

    st.markdown(f"""
    <div class="logo-header" style="display:flex; align-items:center; margin-bottom:20px;">
        <img src="{LEAF_ICON}" style="width:50px; height:50px; margin-right:15px;">
        <h1 style="margin:0;">智影 | 影像私教</h1>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown(f"""
    <div style="background-color: {banner_bg}; padding: 15px; border-radius: 10px; margin-bottom: 20px; color: {'#333' if not st.session_state.dark_mode else '#eee'};">
        <small>{banner_text}</small>
    </div>
    """, unsafe_allow_html=True)

    if st.session_state.user_role == 'guest':
        remain = MAX_GUEST_USAGE - get_guest_usage(st.session_state.user_phone)
        st.markdown(f"""
        <div class="trial-banner">
            🎁 游客试用模式：还剩 <b>{remain}</b> 次机会。满意请联系微信 <b>BayernGomez28</b> 开通会员！
        </div>
        """, unsafe_allow_html=True)

    tab1, tab2 = st.tabs(["📂 上传照片", "📷 现场拍摄"])
    
    with tab1:
        f = st.file_uploader("支持 JPG/PNG", type=["jpg","png","webp"], key="up_file", on_change=clear_camera)
        if f: st.session_state.current_image = Image.open(f).convert('RGB')
            
    with tab2:
        c = st.camera_input("点击拍摄", key="cam_file", on_change=clear_upload)
        if c: st.session_state.current_image = Image.open(c).convert('RGB')

    if st.button("🗑️ 清空重置 / 换张图", use_container_width=True, on_click=reset_all):
        st.rerun()

    if st.session_state.get('current_image'):
        st.divider()
        c1, c2 = st.columns([1, 1.2])
        
        with c1:
            st.image(st.session_state.current_image, caption="待分析影像", use_container_width=True)
            if show_exif_info:
                exif = get_exif_data(st.session_state.current_image)
                if exif:
                    with st.expander("📷 拍摄参数"): st.json(exif)
        
        with c2:
            # === 核心逻辑：带缓存 ===
            # 定义一个函数来调用AI (利用st.cache_data)
            @st.cache_data(show_spinner=False, ttl=3600)
            def generate_ai_analysis(img_bytes, prompt, model_name):
                try:
                    img = Image.open(io.BytesIO(img_bytes))
                    cfg = genai.types.GenerationConfig(temperature=0.0)
                    m = genai.GenerativeModel(model_name, system_instruction=prompt)
                    res = m.generate_content([img, "分析此图。"], generation_config=cfg)
                    return res.text
                except Exception as e:
                    return f"ERROR: {e}"

            if not st.session_state.current_report:
                user_req = st.text_input("备注 (可选):", placeholder="例如：想修出日系感...")
                
                if st.button("🚀 开始评估", type="primary", use_container_width=True):
                    with st.status(status_msg, expanded=True) as s:
                        logger.info(f"⭐⭐⭐ [MONITOR] ACTION | User: {st.session_state.user_phone}")
                        
                        # 转换图片为字节流以使用缓存
                        img_byte_arr = io.BytesIO()
                        st.session_state.current_image.save(img_byte_arr, format='JPEG')
                        img_bytes = img_byte_arr.getvalue()
                        
                        # 调用带缓存的函数
                        ai_result = generate_ai_analysis(img_bytes, active_prompt, real_model)
                        
                        if "ERROR:" in ai_result:
                            st.error(ai_result)
                        else:
                            st.session_state.current_report = ai_result
                            st.session_state.current_req = user_req
                            s.update(label="✅ 分析完成", state="complete", expanded=False)
                            st.rerun()
            
            if st.session_state.current_report:
                st.markdown(f'<div class="result-card">{st.session_state.current_report}</div>', unsafe_allow_html=True)
                
                img_b64 = img_to_base64(st.session_state.current_image)
                if not st.session_state.history or st.session_state.history[-1]['content'] != st.session_state.current_report:
                    record = {"time": datetime.now().strftime("%H:%M"), "mode": mode_select, "content": st.session_state.current_report, "img_base64": img_b64}
                    st.session_state.history.append(record)
                    if len(st.session_state.history) > 5: st.session_state.history.pop(0)

                btn_c1, btn_c2 = st.columns(2)
                with btn_c1:
                    html_report = create_html_report(st.session_state.current_report, st.session_state.get('current_req', ''), img_b64)
                    st.download_button("📥 下载报告", html_report, file_name="智影报告.html", mime="text/html", use_container_width=True)
                
                with btn_c2:
                    if st.button("❤️ 加入收藏", use_container_width=True):
                        record = {"time": datetime.now().strftime("%H:%M"), "mode": mode_select, "content": st.session_state.current_report, "img_base64": img_b64}
                        st.session_state.favorites.append(record)
                        st.toast("已收藏！", icon="⭐")

if __name__ == "__main__":
    if st.session_state.logged_in:
        show_main_app()
    else:
        show_login_page()