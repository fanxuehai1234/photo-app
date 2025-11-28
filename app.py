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
import json # 引入JSON处理，用于数据持久化

# ================= 0. 核心配置 & 日志 =================
warnings.filterwarnings("ignore")
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

st.set_page_config(
    page_title="智影 | AI 影像顾问", 
    page_icon="icon.png", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# ================= 1. CSS 专业级美化 (修复对齐) =================
st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    div[class^="viewerBadge"] {display: none !important;} 
    
    /* 手机端顶部间距优化 */
    .block-container {
        padding-top: 1rem !important;
        padding-bottom: 3rem !important;
    }
    
    /* --- 核心修复：Flexbox 页头对齐布局 --- */
    .header-container {
        display: flex;
        align-items: center; /* 垂直居中核心代码 */
        justify-content: flex-start;
        margin-bottom: 15px;
        padding: 10px;
        background: rgba(255,255,255,0.05); /* 轻微背景增加层次 */
        border-radius: 10px;
    }
    .header-logo {
        width: 50px;
        height: 50px;
        margin-right: 12px;
        object-fit: contain;
    }
    .header-title {
        font-size: 1.8rem;
        font-weight: 700;
        margin: 0;
        padding: 0;
        line-height: 1.2;
        color: inherit; /* 继承父元素颜色以适配深色模式 */
    }
    /* 手机端专门适配 */
    @media (max-width: 768px) {
         .header-logo { width: 40px; height: 40px; margin-right: 10px; }
         .header-title { font-size: 1.5rem; } /* 手机上字号稍微小一点更精致 */
    }

    /* 结果卡片 */
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
    </style>
    """, unsafe_allow_html=True)

# ================= 2. 数据持久化引擎 (商业核心) =================
DATA_DIR = "user_data"
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

def get_user_data_file(phone):
    return os.path.join(DATA_DIR, f"user_{phone}.json")

# 加载用户数据
def load_user_data(phone):
    data_file = get_user_data_file(phone)
    if os.path.exists(data_file):
        try:
            with open(data_file, 'r') as f:
                data = json.load(f)
            logger.info(f"Data loaded for user: {phone}")
            return data.get('history', []), data.get('favorites', [])
        except Exception as e:
            logger.error(f"Failed to load data for {phone}: {e}")
            return [], []
    return [], []

# 保存用户数据 (自动触发)
def save_user_data():
    if st.session_state.logged_in and st.session_state.user_phone:
        phone = st.session_state.user_phone
        data = {
            'history': st.session_state.history,
            'favorites': st.session_state.favorites
        }
        data_file = get_user_data_file(phone)
        try:
            with open(data_file, 'w') as f:
                json.dump(data, f)
            logger.info(f"Data saved for user: {phone}")
        except Exception as e:
            logger.error(f"Failed to save data for {phone}: {e}")

# ================= 3. 状态管理 =================
def init_session_state():
    defaults = {
        'logged_in': False,
        'user_phone': None,
        'expire_date': None,
        'history': [],
        'favorites': [],
        'font_size': 16,
        'dark_mode': False,
        'current_report': None,
        'current_img_b64': None, # 新增：缓存当前图片的base64，防止反复计算
        'processing': False
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

init_session_state()

# 图片互斥清理
def clear_camera():
    if 'cam_file' in st.session_state: del st.session_state['cam_file']
    st.session_state.current_report = None
    st.session_state.current_img_b64 = None

def clear_upload():
    if 'up_file' in st.session_state: del st.session_state['up_file']
    st.session_state.current_report = None
    st.session_state.current_img_b64 = None

def reset_all():
    if 'cam_file' in st.session_state: del st.session_state['cam_file']
    if 'up_file' in st.session_state: del st.session_state['up_file']
    st.session_state.current_report = None
    st.session_state.current_img_b64 = None

# ================= 4. 工具函数 =================
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
    # 优化：压缩图片质量以加快处理速度
    try:
        buffered = io.BytesIO()
        image.save(buffered, format="JPEG", quality=40) # 质量降到40，足够清晰且更快
        return base64.b64encode(buffered.getvalue()).decode()
    except: return ""

# 显示新叶子Logo的专用函数
def show_leaf_logo(width=None):
    if os.path.exists("leaf.png"):
        st.image("leaf.png", width=width)
    else:
        st.write("🌿") # 备用

# ================= 5. 登录页 =================
def show_login_page():
    col_poster, col_login = st.columns([1.2, 1])
    
    with col_poster:
        st.image("https://images.unsplash.com/photo-1516035069371-29a1b244cc32?q=80&w=1000&auto=format&fit=crop", 
                 use_container_width=True)

    with col_login:
        st.markdown("<br>", unsafe_allow_html=True)
        
        # 使用新的 Flexbox 布局头，确保对齐
        st.markdown(f"""
        <div class="header-container">
            <img src="data:image/png;base64,{img_to_base64(Image.open("leaf.png"))}" class="header-logo">
            <h1 class="header-title">智影</h1>
        </div>
        """, unsafe_allow_html=True)
            
        st.markdown("#### 您的 24小时 AI 摄影私教")
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
                        # 登录成功：设置状态并加载数据
                        st.session_state.logged_in = True
                        st.session_state.user_phone = phone_input
                        st.session_state.expire_date = expire_date_str
                        # 🔥 核心：从硬盘加载用户历史数据
                        hist, favs = load_user_data(phone_input)
                        st.session_state.history = hist
                        st.session_state.favorites = favs
                        
                        if 'current_image' in st.session_state: del st.session_state['current_image']
                        logger.info(f"⭐⭐⭐ [MONITOR] LOGIN SUCCESS | User: {phone_input} | Data Loaded")
                        st.rerun()
                    else:
                        st.error("账号或激活码错误")
                except Exception as e:
                    st.error(f"配置错误: {e}")

        st.warning("💎 **获取激活码 / 续费请联系微信：BayernGomez**")
        with st.expander("📲 安装教程"):
            st.markdown("iPhone: Safari分享 -> 添加到主屏幕\nAndroid: Chrome菜单 -> 添加到主屏幕")

# ================= 6. 主程序 =================
def show_main_app():
    if not configure_random_key():
        st.stop()

    # 深色模式适配
    if st.session_state.dark_mode:
        st.markdown("""<style>
        .stApp {background-color: #121212; color: #E0E0E0;}
        .result-card {background-color: #1E1E1E; color: #E0E0E0;}
        section[data-testid="stSidebar"] {background-color: #1E1E1E;}
        [data-baseweb="input"] {background-color: #262626; color: white;}
        .header-title {color: #E0E0E0 !important;} /* 确保标题在深色模式下变白 */
        </style>""", unsafe_allow_html=True)

    with st.sidebar:
        # 侧边栏页头 (使用 Flexbox 对齐)
        st.markdown(f"""
        <div style="display: flex; align-items: center; margin-bottom: 20px;">
            <img src="data:image/png;base64,{img_to_base64(Image.open("leaf.png"))}" style="width: 40px; height: 40px; margin-right: 10px;">
            <h3 style="margin:0; padding:0;">用户中心</h3>
        </div>
        """, unsafe_allow_html=True)
        
        st.info(f"👤 {st.session_state.user_phone}")
        st.caption(f"有效期: {st.session_state.expire_date}")
        
        st.markdown("---")
        mode_select = st.radio("模式选择:", ["📷 日常快评", "🧐 专业艺术"], index=0)

        st.markdown("---")
        # 历史记录 (带图)
        with st.expander("🕒 历史记录", expanded=False):
            if not st.session_state.history:
                st.caption("暂无记录")
            else:
                for idx, item in enumerate(reversed(st.session_state.history)):
                    with st.popover(f"📄 {item['time']} - {item['mode']}"):
                        if item.get('img_base64'):
                            st.markdown(f'<img src="data:image/jpeg;base64,{item["img_base64"]}" width="100%" style="border-radius:5px;">', unsafe_allow_html=True)
                        st.markdown(item['content'])

        # 收藏夹 (带图)
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
            save_user_data() # 退出前保存数据
            st.session_state.logged_in = False
            if 'current_image' in st.session_state: del st.session_state['current_image']
            st.rerun()
            
        st.markdown("---")
        st.caption("Ver: V27.0 Commercial")

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

    # ★★★ 主界面页头 (使用 Flexbox 完美对齐) ★★★
    st.markdown(f"""
    <div class="header-container">
        <img src="data:image/png;base64,{img_to_base64(Image.open("leaf.png"))}" class="header-logo">
        <h1 class="header-title">智影 | 影像私教</h1>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown(f"""
    <div style="background-color: {banner_bg}; padding: 15px; border-radius: 10px; margin-bottom: 20px; color: {'#333' if not st.session_state.dark_mode else '#eee'};">
        <small>{banner_text}</small>
    </div>
    """, unsafe_allow_html=True)

    tab1, tab2 = st.tabs(["📂 上传照片", "📷 现场拍摄"])
    active_image = None
    
    with tab1:
        f = st.file_uploader("支持 JPG/PNG", type=["jpg","png","webp"], key="up_file", on_change=clear_camera)
        if f: active_image = Image.open(f).convert('RGB')
            
    with tab2:
        c = st.camera_input("点击拍摄", key="cam_file", on_change=clear_upload)
        if c: active_image = Image.open(c).convert('RGB')

    if st.button("🗑️ 清空重置 / 换张图", use_container_width=True, on_click=reset_all):
        st.rerun()

    if active_image:
        st.divider()
        c1, c2 = st.columns([1, 1.2])
        
        with c1:
            st.image(active_image, caption="待分析影像", use_container_width=True)
            if show_exif_info:
                exif = get_exif_data(active_image)
                if exif:
                    with st.expander("📷 拍摄参数"): st.json(exif)
        
        with c2:
            if not st.session_state.current_report:
                user_req = st.text_input("备注 (可选):", placeholder="例如：想修出日系感...")
                
                if st.button("🚀 开始评估", type="primary", use_container_width=True):
                    with st.status(status_msg, expanded=True) as s:
                        logger.info(f"⭐⭐⭐ [MONITOR] ACTION | User: {st.session_state.user_phone} | Mode: {mode_select}")
                        
                        generation_config = genai.types.GenerationConfig(temperature=0.1)
                        model = genai.GenerativeModel(real_model, system_instruction=active_prompt)
                        
                        msg = "分析此图。"
                        if user_req: msg += f" 备注：{user_req}"
                        
                        response = model.generate_content([msg, active_image], generation_config=generation_config)
                        
                        # 🔥 核心修复：生成报告的同时，立即生成并缓存图片Base64
                        st.session_state.current_report = response.text
                        st.session_state.current_req = user_req
                        st.session_state.current_img_b64 = img_to_base64(active_image) # 立即缓存，防止后续操作丢失
                        
                        s.update(label="✅ 分析完成", state="complete", expanded=False)
                        st.rerun()
            
            # 只要有报告缓存，就显示报告，不受按钮刷新影响
            if st.session_state.current_report:
                st.markdown(f'<div class="result-card">{st.session_state.current_report}</div>', unsafe_allow_html=True)
                
                # 使用缓存的 Base64，不再重新计算
                img_b64 = st.session_state.current_img_b64
                
                # 自动存入历史 (如果包含新内容)
                if not st.session_state.history or st.session_state.history[-1]['content'] != st.session_state.current_report:
                    record = {"time": datetime.now().strftime("%H:%M"), "mode": mode_select, "content": st.session_state.current_report, "img_base64": img_b64}
                    st.session_state.history.append(record)
                    if len(st.session_state.history) > 5: st.session_state.history.pop(0)
                    save_user_data() # 🔥 立即保存到硬盘

                btn_c1, btn_c2 = st.columns(2)
                with btn_c1:
                    html_report = create_html_report(st.session_state.current_report, st.session_state.get('current_req', ''), img_b64)
                    st.download_button("📥 下载报告", html_report, file_name="智影报告.html", mime="text/html", use_container_width=True)
                
                with btn_c2:
                    # 🔥 核心修复：点击收藏不再丢失内容
                    if st.button("❤️ 加入收藏", use_container_width=True):
                        # 直接从缓存读取数据存入收藏
                        record = {"time": datetime.now().strftime("%H:%M"), "mode": mode_select, "content": st.session_state.current_report, "img_base64": st.session_state.current_img_b64}
                        st.session_state.favorites.append(record)
                        save_user_data() # 🔥 立即保存到硬盘
                        st.toast("已收藏！数据已永久保存。", icon="✅")
                        # 注意：这里不再rerun，利用 Streamlit 的自然刷新机制保持界面稳定

if __name__ == "__main__":
    if st.session_state.logged_in:
        show_main_app()
    else:
        show_login_page()