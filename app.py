import streamlit as st
import google.generativeai as genai
from PIL import Image, ExifTags
import time
from datetime import datetime
import warnings
import random
import os
import logging

# ================= 0. 核心配置 =================
warnings.filterwarnings("ignore")
os.environ['STREAMLIT_logger_level'] = 'error'
logging.getLogger('streamlit').setLevel(logging.ERROR)

st.set_page_config(
    page_title="一叶摇风 | 影像私教", 
    page_icon="🍃", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# ================= 1. CSS 美化 =================
st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .stApp {transition: background-color 0.5s ease;}
    
    /* 侧边栏背景 */
    section[data-testid="stSidebar"] {
        background-color: #f8f9fa;
    }
    
    /* 结果卡片美化 */
    .result-card {
        background-color: #ffffff;
        border-left: 5px solid #4CAF50;
        padding: 25px;
        border-radius: 12px;
        margin-top: 20px;
        margin-bottom: 20px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.08);
        line-height: 1.8; /* 增加行高，让文字更易读 */
    }
    
    /* 强制让一级标题更大更醒目 */
    .result-card h1 {
        color: #2E7D32;
        border-bottom: 1px solid #eee;
        padding-bottom: 10px;
        margin-bottom: 20px;
    }
    </style>
    """, unsafe_allow_html=True)

# ================= 2. 状态初始化 =================
def init_session_state():
    defaults = {
        'logged_in': False,
        'user_phone': None,
        'expire_date': None,
        'history': [],
        'favorites': [],
        'dark_mode': False,
        'font_size': 16
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

init_session_state()

# ================= 3. 动态主题 =================
def apply_theme():
    if st.session_state.dark_mode:
        main_bg = "#1E1E1E"
        text_col = "#E0E0E0"
        card_bg = "#2D2D2D"
        sidebar_bg = "#262626"
    else:
        main_bg = "#FFFFFF"
        text_col = "#333333"
        card_bg = "#FFFFFF"
        sidebar_bg = "#F8F9FA"

    font_px = st.session_state.font_size

    st.markdown(f"""
    <style>
    .stApp {{
        background-color: {main_bg};
        color: {text_col};
    }}
    section[data-testid="stSidebar"] {{
        background-color: {sidebar_bg};
    }}
    .result-card {{
        background-color: {card_bg};
        color: {text_col};
    }}
    .stMarkdown p, .stMarkdown li {{
        font-size: {font_px}px !important;
    }}
    </style>
    """, unsafe_allow_html=True)

apply_theme()

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

def create_html_report(text, user_req):
    return f"""
    <html><body>
    <h2 style='color:#2E7D32'>🍃 一叶摇风 | 影像分析报告</h2>
    <p><b>时间:</b> {datetime.now().strftime('%Y-%m-%d %H:%M')}</p>
    <p><b>备注:</b> {user_req if user_req else '无'}</p>
    <hr>
    {text.replace(chr(10), '<br>').replace('###', '<h3>').replace('# ', '<h1>').replace('**', '<b>')}
    </body></html>
    """

# ================= 5. 登录页 =================
def show_login_page():
    col_poster, col_login = st.columns([1.2, 1])
    with col_poster:
        st.image("https://images.unsplash.com/photo-1552168324-d612d77725e3?q=80&w=1000&auto=format&fit=crop", 
                 use_container_width=True)
        st.caption("“让每一张照片，都拥有灵魂。”")

    with col_login:
        st.markdown("<br>", unsafe_allow_html=True)
        st.title("🍃 一叶摇风")
        st.markdown("#### 您的 24小时 AI 摄影私教")
        
        st.markdown("""
        <div style="background-color:#f0f2f6; padding:15px; border-radius:10px; margin-bottom:10px; color:#333;">
        ✨ <b>一键评分</b>：AI 专业美学打分<br>
        📊 <b>参数直出</b>：Lightroom / 醒图 数值<br>
        🎓 <b>大师指导</b>：构图与光影建议
        </div>
        """, unsafe_allow_html=True)
        
        with st.container(border=True):
            st.subheader("🔐 会员登录")
            phone_input = st.text_input("手机号码", placeholder="请输入手机号", max_chars=11)
            code_input = st.text_input("激活码 / Key", placeholder="请输入专属 Key", type="password")
            
            if st.button("立即登录", type="primary", use_container_width=True):
                if len(phone_input) != 11:
                    st.error("手机号格式错误")
                    return
                try:
                    valid_accounts = st.secrets["VALID_ACCOUNTS"]
                except:
                    st.error("系统维护中")
                    return

                login_success = False
                expire_date_str = ""
                for account_str in valid_accounts:
                    try:
                        parts = account_str.split(":")
                        if len(parts) == 3 and phone_input == parts[0].strip() and code_input == parts[1].strip():
                            exp_date = datetime.strptime(parts[2].strip(), "%Y-%m-%d")
                            if datetime.now() > exp_date:
                                st.error(f"❌ 会员已于 {parts[2]} 到期")
                                return
                            login_success = True
                            expire_date_str = parts[2]
                            break
                    except: continue

                if login_success:
                    st.session_state.logged_in = True
                    st.session_state.user_phone = phone_input
                    st.session_state.expire_date = expire_date_str
                    st.session_state.history = []
                    st.session_state.favorites = []
                    st.rerun()
                else:
                    st.error("账号或激活码错误")

        st.warning("💎 **获取激活码 / 续费请联系微信：BayernGomez**")
        with st.expander("📲 安装教程"):
            st.markdown("iPhone: Safari分享 -> 添加到主屏幕\nAndroid: Chrome菜单 -> 添加到主屏幕")

# ================= 6. 主程序 (提示词大修版) =================
def show_main_app():
    if not configure_random_key():
        st.stop()

    # --- 侧边栏 ---
    with st.sidebar:
        st.title("🍃 用户中心")
        st.info(f"👤 {st.session_state.user_phone}")
        if st.session_state.expire_date:
            st.caption(f"📅 有效期: {st.session_state.expire_date}")
        
        st.markdown("---")
        st.markdown("**⚙️ 模式选择**")
        mode_select = st.radio(
            "选择分析深度:", 
            ["📷 日常快评 (生活照)", "🧐 专业艺术 (作品集)"],
            index=0,
            label_visibility="collapsed"
        )

        st.markdown("---")
        with st.expander("🕒 最近历史", expanded=False):
            if not st.session_state.history:
                st.caption("暂无记录")
            else:
                for idx, item in enumerate(reversed(st.session_state.history)):
                    st.text(f"{item['time']} - {item['mode']}")
                    with st.popover(f"查看 #{len(st.session_state.history)-idx}"):
                        st.markdown(item['content'])

        with st.expander("❤️ 我的收藏", expanded=False):
            if not st.session_state.favorites:
                st.caption("暂无收藏")
            else:
                for idx, item in enumerate(st.session_state.favorites):
                    with st.popover(f"⭐ 收藏 #{idx+1}"):
                        st.markdown(item['content'])

        st.markdown("---")
        with st.expander("🛠️ 个性化设置", expanded=True):
            # 字体设置
            new_size = st.slider("Aa 字体大小", 14, 24, st.session_state.font_size)
            if new_size != st.session_state.font_size:
                st.session_state.font_size = new_size
                st.rerun()
            
            # 深色模式
            new_dark = st.toggle("🌙 沉浸深色模式", value=st.session_state.dark_mode)
            if new_dark != st.session_state.dark_mode:
                st.session_state.dark_mode = new_dark
                st.rerun()
            
            show_exif_info = st.checkbox("📷 显示拍摄参数", value=True)

        if st.button("退出登录", use_container_width=True):
            st.session_state.logged_in = False
            st.rerun()
            
        st.markdown("---")
        st.caption(f"Ver: V15.0 Final")

    # --- 提示词 (核心修复：强制换行) ---
    # 使用三引号分行写，确保 AI 理解结构
    
    if "日常" in mode_select:
        real_model = "gemini-2.0-flash-lite-preview-02-05"
        btn_label = "🚀 开始评估 (获取手机参数)"
        status_msg = "✨ 正在生成手机修图方案..."
        banner_bg = "#e8f5e9" if not st.session_state.dark_mode else "#1b5e20"
        banner_icon = "🍃"
        banner_text = "日常记录 | 适用：朋友圈、手机摄影、快速出片"
        
        # 修复版提示词：增加了大量换行符 \n\n
        active_prompt = """
        你是一位亲切的摄影博主“一叶摇风”。
        请严格按照 Markdown 格式输出，**确保标题和正文之间有空行**。
        
        输出格式如下：
        
        # 🌟 综合评分: {分数}/10
        
        ### 📝 影像笔记
        > {这里写点评}
        
        ### 🎨 手机修图参数表 (Wake/iPhone)
        | 参数 | 数值 | 目的 |
        | :--- | :--- | :--- |
        | ... | ... | ... |
        
        ### 📸 随手拍建议
        {给出建议}
        
        ---
        **🍃 一叶摇风寄语:** {金句}
        """
        
    else:
        real_model = "gemini-2.5-flash"
        btn_label = "💎 深度解析 (获取专业面板)"
        status_msg = "🧠 正在进行商业级光影分析..."
        banner_bg = "#e3f2fd" if not st.session_state.dark_mode else "#0d47a1"
        banner_icon = "🎓"
        banner_text = "专业创作 | 适用：单反微单、商业修图、作品集"
        
        # 修复版提示词：增加了大量换行符 \n\n
        active_prompt = """
        你是一位视觉艺术总监“一叶摇风”。
        请严格按照 Markdown 格式输出，**确保标题和正文之间有空行**。
        
        输出格式如下：
        
        # 🏆 艺术总评: {分数}/10
        
        ### 👁️ 视觉与美学解析
        {详细分析}
        
        ### 🎨 商业后期面板 (Lightroom/C1)
        | 模块 | 参数 | 建议数值 |
        | :--- | :--- | :--- |
        | ... | ... | ... |
        
        ### 🎓 大师进阶课
        {进阶建议}
        
        ---
        **🍃 一叶摇风寄语:** {哲理}
        """

    # --- 主界面 ---
    st.title("🍃 一叶摇风 | 影像私教")
    
    st.markdown(f"""
    <div style="background-color: {banner_bg}; padding: 15px; border-radius: 10px; margin-bottom: 20px; color: {'#333' if not st.session_state.dark_mode else '#eee'};">
        <h4 style="margin:0; padding:0;">{banner_icon} 当前模式：{mode_select.split(' ')[1]}</h4>
        <small>{banner_text}</small>
    </div>
    """, unsafe_allow_html=True)

    tab1, tab2 = st.tabs(["📂 上传照片", "📷 现场拍摄"])
    img_file = None
    
    with tab1:
        f = st.file_uploader("支持 JPG/PNG/WEBP", type=["jpg","png","webp"], key="up_file")
        if f: img_file = f
    with tab2:
        c = st.camera_input("点击拍摄", key="cam_file")
        if c: img_file = c

    if img_file:
        st.divider()
        try:
            image = Image.open(img_file).convert('RGB')
            c1, c2 = st.columns([1, 1.2])
            
            with c1:
                st.image(image, caption="待分析影像", use_container_width=True)
                if show_exif_info:
                    exif = get_exif_data(image)
                    if exif:
                        with st.expander("📷 拍摄参数 (EXIF)"):
                            st.json(exif)
            
            with c2:
                user_req = st.text_input("备注 (可选):", placeholder="例如：我想修出日系通透感...")
                
                # 按钮组
                b_col1, b_col2 = st.columns([3, 1])
                with b_col1:
                    start_analyze = st.button(btn_label, type="primary", use_container_width=True)
                with b_col2:
                    if st.button("🗑️ 重置", use_container_width=True):
                        st.rerun()

                if start_analyze:
                    with st.status(status_msg, expanded=True) as s:
                        print(f"ACTION: User [{st.session_state.user_phone}] - Mode [{mode_select}]")
                        
                        model = genai.GenerativeModel(real_model, system_instruction=active_prompt)
                        msg = "分析此图。"
                        if user_req: msg += f" 备注：{user_req}"
                        
                        response = model.generate_content([msg, image])
                        s.update(label="✅ 分析完成", state="complete", expanded=False)
                    
                    result_text = response.text
                    
                    # 结果展示
                    st.markdown(f'<div class="result-card">{result_text}</div>', unsafe_allow_html=True)
                    
                    # 历史记录
                    record = {"time": datetime.now().strftime("%H:%M"), "mode": mode_select, "content": result_text}
                    st.session_state.history.append(record)
                    if len(st.session_state.history) > 5: st.session_state.history.pop(0)

                    btn_c1, btn_c2 = st.columns(2)
                    with btn_c1:
                        html_report = create_html_report(result_text, user_req)
                        st.download_button("📥 下载精美报告", html_report, file_name="一叶摇风报告.html", mime="text/html", use_container_width=True)
                    with btn_c2:
                        if st.button("❤️ 加入收藏", use_container_width=True):
                            st.session_state.favorites.append(record)
                            st.toast("已收藏！", icon="⭐")

        except Exception as e:
            st.error("分析中断")
            err = str(e)
            if "429" in err:
                st.warning("⚠️ 额度已满或繁忙，请重试")
            elif "404" in err:
                st.warning("⚠️ 模型暂不可用，请切换模式")
            else:
                st.warning(f"错误: {err}")

if __name__ == "__main__":
    if st.session_state.logged_in:
        show_main_app()
    else:
        show_login_page()