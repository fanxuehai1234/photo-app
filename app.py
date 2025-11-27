import streamlit as st
import google.generativeai as genai
from PIL import Image, ExifTags
import time
from datetime import datetime
import warnings
import random

# ================= 0. 核心配置 =================
# 当前版本号 (每次您更新代码时，手动改一下这个数字，用户就能看到了)
APP_VERSION = "V9.0 (多线路稳定版)"

warnings.filterwarnings("ignore")

st.set_page_config(
    page_title="一叶摇风 | 影像私教", 
    page_icon="🍃", 
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .stApp {transition: background-color 0.5s ease;}
    </style>
    """, unsafe_allow_html=True)

# ================= 1. 智能 Key 管理系统 =================
def configure_random_key():
    try:
        # 读取 Key 列表
        keys = st.secrets["API_KEYS"]
        
        # 兼容处理：如果是字符串转为列表，如果是列表直接用
        if isinstance(keys, str):
            key_list = [keys]
        else:
            key_list = keys
            
        # 随机抽取
        current_key = random.choice(key_list)
        
        # 配置 Google
        genai.configure(api_key=current_key)
        return True
    except Exception as e:
        st.error(f"⚠️ 系统配置错误：{e}")
        return False

# ================= 2. 登录验证系统 =================
def check_login():
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
        st.session_state.user_phone = None
        st.session_state.expire_date = None

    if st.session_state.logged_in:
        return True

    col_poster, col_login = st.columns([1.2, 1])
    
    with col_poster:
        st.image("https://images.unsplash.com/photo-1492691527719-9d1e07e534b4?q=80&w=1000&auto=format&fit=crop", 
                 use_container_width=True)
        st.caption("“摄影不仅是记录，更是表达。”")

    with col_login:
        st.markdown("<br>", unsafe_allow_html=True)
        st.title("🍃 一叶摇风")
        st.markdown(f"#### 您的 24小时 AI 摄影私教 <span style='font-size:12px;color:gray'>{APP_VERSION}</span>", unsafe_allow_html=True)
        
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

# ================= 3. 辅助功能 =================
def get_exif_data(image):
    exif_data = {}
    try:
        info = image._getexif()
        if info:
            for tag, value in info.items():
                decoded = ExifTags.TAGS.get(tag, tag)
                if decoded in ['Make', 'Model', 'DateTimeOriginal', 'ISOSpeedRatings', 'FNumber', 'ExposureTime']:
                    exif_data[decoded] = value
    except:
        pass
    return exif_data

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

    with st.sidebar:
        st.title("🍃 用户中心")
        st.info(f"用户: {st.session_state.user_phone}")
        if st.session_state.expire_date:
            st.caption(f"有效期至: {st.session_state.expire_date}")
        
        st.divider()
        st.write("**⚙️ 模式选择**")
        mode_select = st.radio(
            "选择分析深度:", 
            ["📷 日常快评 (生活照)", "🧐 专业艺术 (作品集)"],
            index=0
        )
        
        with st.expander("🛠️ 个性化设置", expanded=False):
            font_size = st.slider("Aa 字体大小", 14, 24, 16)
            dark_mode = st.toggle("🌙 沉浸深色模式")
            show_exif_info = st.checkbox("📷 显示拍摄参数", value=True)

        bg_color = "#1e1e1e" if dark_mode else "#ffffff"
        text_color = "#ffffff" if dark_mode else "#000000"
        
        st.markdown(f"""
        <style>
        .stApp {{
            background-color: {bg_color};
            color: {text_color};
        }}
        .stMarkdown p, .stMarkdown li {{
            font-size: {font_size}px !important;
        }}
        </style>
        """, unsafe_allow_html=True)

        st.divider()
        # === 底部显示版本号 ===
        st.caption(f"当前版本: {APP_VERSION}")
        
        if st.button("退出登录", use_container_width=True):
            st.session_state.logged_in = False
            st.rerun()

    if "日常" in mode_select:
        real_model = "gemini-2.0-flash-lite-preview-02-05"
        active_prompt = PROMPT_DAILY
        btn_label = "🚀 开始评估 (获取手机参数)"
        status_msg = "✨ 正在生成手机修图方案..."
    else:
        real_model = "gemini-2.5-flash"
        active_prompt = PROMPT_PRO
        btn_label = "💎 深度解析 (获取专业面板)"
        status_msg = "🧠 正在进行商业级光影分析..."

    st.title("🍃 一叶摇风 | 影像私教")
    
    if "日常" in mode_select:
        st.success("当前模式：**日常记录** | 适用：手机摄影、朋友圈打卡")
    else:
        st.info("当前模式：**专业创作** | 适用：单反/微单摄影、商业修图")

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
                        with st.expander("📷 照片详细参数 (EXIF)"):
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
                    
                    st.markdown(response.text)
                    
                    st.download_button(
                        label="📥 下载分析报告",
                        data=response.text,
                        file_name="一叶摇风_修图建议.md",
                        mime="text/markdown"
                    )
                    
        except Exception as e:
            st.error("分析中断")
            err = str(e)
            if "429" in err:
                st.warning("⚠️ 额度已满，请点击按钮重试 (系统会自动切换备用线路)")
            elif "404" in err:
                st.warning("⚠️ 模型暂不可用，请切换模式")
            else:
                st.warning(f"错误: {err}")

if __name__ == "__main__":
    if check_login():
        main_app()