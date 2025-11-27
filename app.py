import streamlit as st
import google.generativeai as genai
from PIL import Image, ExifTags
import time
from datetime import datetime
import warnings
import random
import base64

# ================= 0. 核心配置 =================
warnings.filterwarnings("ignore")
st.set_page_config(
    page_title="一叶摇风 | 影像私教", 
    page_icon="🍃", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS 美化
st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .stApp {transition: background-color 0.5s ease;}
    [data-testid="stSidebar"] {background-color: #f8f9fa;}
    .result-card {
        background-color: #ffffff;
        padding: 20px;
        border-radius: 10px;
        border: 1px solid #e0e0e0;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        margin-top: 20px;
    }
    </style>
    """, unsafe_allow_html=True)

# ================= 1. 初始化状态 (修复报错的核心) =================
def init_session():
    # 强制检查每一个变量，没有就创建
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
    if 'user_phone' not in st.session_state:
        st.session_state.user_phone = None
    if 'expire_date' not in st.session_state:
        st.session_state.expire_date = None
    if 'history' not in st.session_state:
        st.session_state.history = []  # 👈 之前报错就是缺这个
    if 'favorites' not in st.session_state:
        st.session_state.favorites = []

# 运行初始化
init_session()

# ================= 2. 功能函数库 =================
def configure_random_key():
    try:
        keys = st.secrets["API_KEYS"]
        key_list = [keys] if isinstance(keys, str) else keys
        current_key = random.choice(key_list)
        genai.configure(api_key=current_key)
        return True
    except Exception as e:
        st.error(f"⚠️ 系统配置错误：{e}")
        return False

def get_exif_data(image):
    exif_data = {}
    try:
        info = image._getexif()
        if info:
            for tag, value in info.items():
                decoded = ExifTags.TAGS.get(tag, tag)
                if decoded in ['Make', 'Model', 'ISO', 'FNumber', 'ExposureTime', 'DateTimeOriginal']:
                    exif_data[decoded] = value
    except: pass
    return exif_data

def create_html_report(text, user_req):
    # 生成可下载的 HTML 报告
    html = f"""
    <html>
    <head>
        <style>
            body {{ font-family: 'Microsoft YaHei', sans-serif; padding: 40px; line-height: 1.6; color: #333; }}
            .header {{ text-align: center; border-bottom: 2px solid #4CAF50; padding-bottom: 20px; margin-bottom: 30px; }}
            .title {{ font-size: 24px; font-weight: bold; color: #2E7D32; }}
            .meta {{ color: #666; font-size: 14px; margin-top: 10px; }}
            .content {{ background: #f9f9f9; padding: 20px; border-radius: 8px; }}
            h1, h2, h3 {{ color: #2E7D32; }}
            table {{ border-collapse: collapse; width: 100%; margin: 20px 0; }}
            th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
            th {{ background-color: #4CAF50; color: white; }}
        </style>
    </head>
    <body>
        <div class="header">
            <div class="title">🍃 一叶摇风 | 影像分析报告</div>
            <div class="meta">生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}</div>
            <div class="meta">用户备注: {user_req if user_req else "无"}</div>
        </div>
        <div class="content">
            {text.replace(chr(10), '<br>').replace('###', '<h3>').replace('# ', '<h1>').replace('**', '<b>')}
        </div>
    </body>
    </html>
    """
    return html

# ================= 3. 登录逻辑 =================
def check_login():
    if st.session_state.logged_in:
        return True

    col_poster, col_login = st.columns([1.2, 1])
    with col_poster:
        st.image("https://images.unsplash.com/photo-1492691527719-9d1e07e534b4?q=80&w=1000&auto=format&fit=crop", use_container_width=True)
        st.caption("“摄影不仅是记录，更是表达。”")

    with col_login:
        st.markdown("<br>", unsafe_allow_html=True)
        st.title("🍃 一叶摇风")
        st.markdown(f"#### 您的 24小时 AI 摄影私教 <span style='font-size:12px;color:gray'>V10.1 修复版</span>", unsafe_allow_html=True)
        
        with st.container(border=True):
            st.subheader("🔐 会员登录")
            phone_input = st.text_input("手机号码", placeholder="请输入手机号", max_chars=11)
            code_input = st.text_input("激活码 / Key", placeholder="请输入专属 Key", type="password")
            
            if st.button("立即登录", type="primary", use_container_width=True):
                if len(phone_input) != 11:
                    st.error("手机号格式错误")
                    return False
                try:
                    valid_accounts = st.secrets["VALID_ACCOUNTS"]
                except:
                    st.error("系统维护中")
                    return False

                login_success = False
                expire_date_str = ""
                for account_str in valid_accounts:
                    try:
                        parts = account_str.split(":")
                        if len(parts) == 3:
                            if phone_input == parts[0].strip() and code_input == parts[1].strip():
                                exp_date = datetime.strptime(parts[2].strip(), "%Y-%m-%d")
                                if datetime.now() > exp_date:
                                    st.error(f"❌ 会员已于 {parts[2]} 到期")
                                    return False
                                login_success = True
                                expire_date_str = parts[2]
                                break
                    except: continue

                if login_success:
                    st.session_state.logged_in = True
                    st.session_state.user_phone = phone_input
                    st.session_state.expire_date = expire_date_str
                    # 重新初始化一次以防万一
                    st.session_state.history = []
                    st.session_state.favorites = []
                    st.toast("登录成功！", icon="🎉")
                    time.sleep(0.5)
                    st.rerun()
                else:
                    st.error("账号或激活码错误")
                    return False

        st.warning("💎 **获取激活码 / 续费请联系微信：BayernGomez**")
        with st.expander("📲 安装教程 (点我展开)"):
            st.markdown("iPhone: Safari分享 -> 添加到主屏幕\n\nAndroid: Chrome菜单 -> 添加到主屏幕")
    return False

# ================= 4. 主程序 =================
def main_app():
    if not configure_random_key():
        st.stop()

    PROMPT_DAILY = """
    你是一位亲切的摄影博主“一叶摇风”。
    请输出 Markdown：
    # 🌟 综合评分: {分数}/10
    ### 📝 影像笔记
    ### 🎨 手机修图参数表 (Wake/iPhone)
    | 参数 | 数值 | 目的 |
    | :--- | :--- | :--- |
    | ... | ... | ... |
    ### 📸 随手拍建议
    ---
    **🍃 一叶摇风寄语:** {金句}
    """
    
    PROMPT_PRO = """
    你是一位视觉艺术总监“一叶摇风”。
    请输出 Markdown：
    # 🏆 艺术总评: {分数}/10
    ### 👁️ 视觉与美学解析
    ### 🎨 商业后期面板 (Lightroom/C1)
    | 模块 | 参数 | 建议数值 |
    | :--- | :--- | :--- |
    | ... | ... | ... |
    ### 🎓 大师进阶课
    ---
    **🍃 一叶摇风寄语:** {哲理}
    """

    # --- 侧边栏 ---
    with st.sidebar:
        st.title("🍃 用户中心")
        st.info(f"👤 {st.session_state.user_phone}")
        st.caption(f"📅 有效期: {st.session_state.expire_date}")
        
        st.markdown("---")
        st.markdown("**⚙️ 模式选择**")
        mode_select = st.radio(
            "选择分析深度:", 
            ["📷 日常快评", "🧐 专业艺术"],
            index=0,
            label_visibility="collapsed"
        )

        # --- 历史记录与收藏 ---
        st.markdown("---")
        # 确保 history 存在，防止报错
        if 'history' not in st.session_state: st.session_state.history = []
        if 'favorites' not in st.session_state: st.session_state.favorites = []

        with st.expander("🕒 最近历史 (Last 5)", expanded=False):
            if not st.session_state.history:
                st.caption("暂无记录")
            else:
                for idx, item in enumerate(reversed(st.session_state.history)):
                    st.text(f"{item['time']} - {item['mode']}")
                    with st.popover(f"查看记录 #{len(st.session_state.history)-idx}"):
                        st.markdown(item['content'])

        with st.expander("❤️ 我的收藏", expanded=False):
            if not st.session_state.favorites:
                st.caption("暂无收藏")
            else:
                for idx, item in enumerate(st.session_state.favorites):
                    with st.popover(f"⭐ 收藏 #{idx+1} ({item['time']})"):
                        st.markdown(item['content'])

        st.markdown("---")
        with st.expander("🛠️ 个性化设置"):
            font_size = st.slider("字体大小", 14, 24, 16)
            show_exif_info = st.checkbox("显示参数(EXIF)", value=True)
        
        st.markdown(f"<style>.stMarkdown p, .stMarkdown li {{font-size: {font_size}px !important;}}</style>", unsafe_allow_html=True)

        if st.button("退出登录", use_container_width=True):
            st.session_state.logged_in = False
            st.rerun()

    # --- 路由 ---
    if "日常" in mode_select:
        real_model = "gemini-2.0-flash-lite-preview-02-05"
        active_prompt = PROMPT_DAILY
        btn_label = "🚀 开始评估 (获取手机参数)"
        status_msg = "✨ 正在生成手机修图方案..."
        banner_color = "rgba(76, 175, 80, 0.1)"
        banner_icon = "🍃"
    else:
        real_model = "gemini-2.5-flash"
        active_prompt = PROMPT_PRO
        btn_label = "💎 深度解析 (获取专业面板)"
        status_msg = "🧠 正在进行商业级光影分析..."
        banner_color = "rgba(33, 150, 243, 0.1)"
        banner_icon = "🎓"

    # --- 主界面 ---
    st.title("🍃 一叶摇风 | 影像私教")
    
    st.markdown(f"""
    <div style="background-color: {banner_color}; padding: 15px; border-radius: 10px; margin-bottom: 20px;">
        <h4 style="margin:0; padding:0;">{banner_icon} 当前模式：{mode_select.split(' ')[1]}</h4>
        <small style="color: gray;">适用于：{'朋友圈、生活记录、快速出片' if '日常' in mode_select else '商业摄影、作品集、精修'}</small>
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
                
                if st.button(btn_label, type="primary", use_container_width=True):
                    with st.status(status_msg, expanded=True) as s:
                        print(f"ACTION: User [{st.session_state.user_phone}] - Mode [{mode_select}]")
                        
                        model = genai.GenerativeModel(real_model, system_instruction=active_prompt)
                        msg = "分析此图。"
                        if user_req: msg += f" 备注：{user_req}"
                        
                        response = model.generate_content([msg, image])
                        s.update(label="✅ 分析完成", state="complete", expanded=False)
                    
                    result_text = response.text
                    st.markdown(f'<div class="result-card">{result_text}</div>', unsafe_allow_html=True)
                    st.markdown(result_text)
                    
                    # 写入历史记录
                    timestamp = datetime.now().strftime("%H:%M")
                    record = {"time": timestamp, "mode": mode_select, "content": result_text}
                    st.session_state.history.append(record)
                    if len(st.session_state.history) > 5:
                        st.session_state.history.pop(0)

                    btn_col1, btn_col2 = st.columns(2)
                    with btn_col1:
                        html_report = create_html_report(result_text, user_req)
                        st.download_button(
                            label="📥 下载精美报告",
                            data=html_report,
                            file_name=f"一叶摇风_修图建议.html",
                            mime="text/html",
                            use_container_width=True
                        )
                    with btn_col2:
                        if st.button("❤️ 加入收藏夹", use_container_width=True):
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
    if check_login():
        main_app()