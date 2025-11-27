import streamlit as st
import google.generativeai as genai
from PIL import Image
import time
from datetime import datetime

# ================= 1. 全局配置 & CSS美化 =================
st.set_page_config(
    page_title="一叶摇风 | 影像私教", 
    page_icon="🍃", 
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- 注入 CSS 隐藏多余元素，打造沉浸式 App 感 ---
st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .stApp {
        background-color: #ffffff;
    }
    /* 优化手机端显示 */
    [data-testid="stVerticalBlock"] {
        gap: 1rem;
    }
    </style>
    """, unsafe_allow_html=True)

# ================= 2. 登录验证系统 (商业优化版) =================
def check_login():
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
        st.session_state.user_phone = None
        st.session_state.expire_date = None

    if st.session_state.logged_in:
        return True

    # --- 布局优化：使用更紧凑的列比例 ---
    # 空白 : 图片 : 登录框 : 空白
    # 这样可以让登录框在电脑上看起来更聚气
    col_padding1, col_img, col_login, col_padding2 = st.columns([0.5, 3, 2.5, 0.5])
    
    # --- 左侧：视觉海报 ---
    with col_img:
        # 换了一张更有意境、色调更高级的竖版摄影图
        st.image("https://images.unsplash.com/photo-1492691527719-9d1e07e534b4?q=80&w=1000&auto=format&fit=crop", 
                 use_container_width=True)
        
        # 在图片下方加简短标语，手机上也能看到
        st.caption("“摄影不仅是记录，更是表达。” —— 一叶摇风")

    # --- 右侧：登录核心区 ---
    with col_login:
        st.markdown("<br>", unsafe_allow_html=True) # 顶部留白微调
        
        # 品牌 Logo 区
        st.title("🍃 一叶摇风")
        st.markdown("#### 您的 24小时 AI 摄影私教")
        
        # 功能亮点 (用更精炼的列表)
        st.markdown("""
        <style>
        .feature-box {
            background-color: #f0f2f6;
            padding: 15px;
            border-radius: 10px;
            font-size: 14px;
            margin-bottom: 20px;
        }
        </style>
        <div class="feature-box">
        ✨ <b>一键评分</b>：AI 专业美学打分<br>
        📊 <b>修图参数</b>：直接生成修图数值表<br>
        🎓 <b>拍摄指导</b>：大师级构图建议
        </div>
        """, unsafe_allow_html=True)
        
        # 登录表单
        with st.container(border=True):
            st.subheader("🔐 会员登录")
            
            phone_input = st.text_input("手机号码", placeholder="请输入手机号", max_chars=11)
            code_input = st.text_input("激活码 / Key", placeholder="请输入您的专属 Key", type="password")
            
            if st.button("立即登录", type="primary", use_container_width=True):
                # 校验逻辑
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
                    print(f"LOGIN SUCCESS: [{phone_input}]")
                    st.toast("登录成功！正在跳转...", icon="🎉")
                    time.sleep(0.5)
                    st.rerun()
                else:
                    st.error("账号或激活码错误")
                    return False

        # === 💰 变现入口 (高亮显示) ===
        st.warning("💎 **获取激活码 / 续费请联系微信：BayernGomez**")
        
        st.caption("⚠️ 提示：账号仅限本人使用，多设备登录将自动封号。")

        # 安装教程 (折叠)
        with st.expander("📲 点我查看：如何安装到手机桌面？"):
            st.markdown("iPhone: Safari分享 -> 添加到主屏幕\n\nAndroid: Chrome菜单 -> 添加到主屏幕")

    return False

# ================= 3. 主程序 (保持不变) =================
def main_app():
    try:
        api_key = st.secrets["GOOGLE_API_KEY"]
        genai.configure(api_key=api_key)
    except:
        st.error("API Key 缺失")
        st.stop()

    PROMPT_DAILY = """
    你是一位亲切的摄影博主“一叶摇风”。
    请输出 Markdown：
    # 🌟 综合评分: {分数}/10
    ### 📝 影像笔记
    ### 🎨 手机修图参数表 (表格形式)
    ### 📸 拍摄建议
    ---
    **🍃 一叶摇风寄语:** {金句}
    """
    
    PROMPT_PRO = """
    你是一位视觉艺术总监“一叶摇风”。
    请输出 Markdown：
    # 🏆 艺术总评: {分数}/10
    ### 👁️ 视觉解析
    ### 🎨 商业后期面板 (LR参数表格)
    ### 🎓 进阶指导
    ---
    **🍃 一叶摇风寄语:** {哲理}
    """

    with st.sidebar:
        st.title("🍃 用户中心")
        st.success(f"📱 用户: {st.session_state.user_phone}")
        if st.session_state.expire_date:
            st.caption(f"📅 有效期: {st.session_state.expire_date}")
        if st.button("退出登录"):
            st.session_state.logged_in = False
            st.rerun()
        st.divider()
        
        mode = st.radio("模式选择:", ["📷 日常快评", "🧐 专业艺术"], captions=["2.0 Flash Lite", "2.5 Flash"])
        
        if "日常" in mode:
            real_model = "gemini-2.0-flash-lite-preview-02-05"
            active_prompt = PROMPT_DAILY
            btn_label = "🚀 获取手机参数"
        else:
            real_model = "gemini-2.5-flash"
            active_prompt = PROMPT_PRO
            btn_label = "💎 获取专业面板"

    st.title("🍃 一叶摇风 | 影像私教")
    
    col1, col2 = st.columns(2)
    img_file = None
    with col1:
        f = st.file_uploader("上传照片", key="up")
        if f: img_file = f
    with col2:
        c = st.camera_input("拍摄", key="cam")
        if c: img_file = c

    if img_file:
        st.divider()
        try:
            image = Image.open(img_file).convert('RGB')
            c_img, c_txt = st.columns([1, 1.2])
            with c_img: st.image(image, use_container_width=True)
            with c_txt:
                user_req = st.text_input("备注 (可选):")
                if st.button(btn_label, type="primary", use_container_width=True):
                    with st.status("🧠 分析中...", expanded=True) as s:
                        print(f"ACTION: User [{st.session_state.user_phone}] processed image.")
                        model = genai.GenerativeModel(real_model, system_instruction=active_prompt)
                        msg = "分析此图。"
                        if user_req: msg += f" 备注：{user_req}"
                        res = model.generate_content([msg, image])
                        s.update(label="✅ 完成", state="complete", expanded=False)
                    st.markdown(res.text)
        except Exception as e:
            st.error(f"Error: {e}")

if __name__ == "__main__":
    if check_login():
        main_app()