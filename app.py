import streamlit as st
import google.generativeai as genai
from PIL import Image
import time

# ================= 1. 全局配置 =================
st.set_page_config(
    page_title="一叶摇风 | 影像私教", 
    page_icon="🍃", 
    layout="wide",
    initial_sidebar_state="collapsed" # 登录前收起侧边栏，更沉浸
)

# ================= 2. 登录验证系统 (海报版) =================
def check_login():
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
        st.session_state.user_phone = None

    if st.session_state.logged_in:
        return True

    # --- 登录页排版：左图右文 ---
    # 定义两列，左边宽一点放图，右边放登录框
    col_poster, col_login = st.columns([1.2, 1])
    
    with col_poster:
        # 这里使用了一张 Unsplash 的专业摄影题材高清图 (无需您上传)
        st.image("https://images.unsplash.com/photo-1516035069371-29a1b244cc32?q=80&w=1000&auto=format&fit=crop", 
                 caption="Capture the moment. Analyze the soul.", 
                 use_container_width=True)

    with col_login:
        st.markdown("<br>", unsafe_allow_html=True) # 顶部留白
        st.title("🍃 一叶摇风影像")
        st.markdown("##### 专业的 AI 摄影私教与后期顾问")
        st.caption("会员制服务 | 手机号实名登录")
        
        st.divider()
        
        # === 登录卡片 ===
        with st.container(border=True):
            phone_input = st.text_input("📱 手机号码", placeholder="请输入您的手机号", max_chars=11)
            code_input = st.text_input("🔑 会员激活码", placeholder="请输入购买的 Key", type="password")
            
            if st.button("立即登录 / Login", type="primary", use_container_width=True):
                # 校验手机号
                if len(phone_input) != 11 or not phone_input.isdigit():
                    st.error("请填写正确的 11 位手机号码")
                    return False
                
                # 校验激活码
                try:
                    valid_keys = st.secrets["VALID_KEYS"]
                except:
                    st.error("系统配置错误，请联系管理员")
                    return False

                if code_input in valid_keys:
                    st.session_state.logged_in = True
                    st.session_state.user_phone = phone_input
                    # 关键：记录日志，方便您在后台查岗
                    print(f"✅ LOGIN SUCCESS: Phone [{phone_input}] used Key [{code_input}]")
                    st.success("验证通过，正在进入工作室...")
                    time.sleep(0.5)
                    st.rerun()
                else:
                    # 记录失败日志
                    print(f"❌ LOGIN FAILED: Phone [{phone_input}] tried Key [{code_input}]")
                    st.error("激活码错误或已失效")
                    return False

        # === 安装教程 (折叠) ===
        with st.expander("📲 必读：如何安装到手机桌面？"):
            st.markdown("""
            **🍎 iPhone 用户:** 用 Safari 打开 -> 点击底部[分享] -> 选择 [添加到主屏幕]。
            
            **🤖 安卓 用户:** 用 Chrome/Edge 打开 -> 点击右上角菜单 -> [添加到主屏幕] 或 [安装应用]。
            """)
            
        st.caption("遇见光影，预见更好的自己。")
    
    return False

# ================= 3. 主程序逻辑 (保持完美版) =================
def main_app():
    # 读取 Key
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
        st.info(f"当前用户: {st.session_state.user_phone}")
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
        f = st.file_uploader("上传照片", type=["jpg","png","webp"], key="up")
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
                        print(f"ACTION: Phone [{st.session_state.user_phone}] processed image.")
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