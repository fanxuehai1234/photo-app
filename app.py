import streamlit as st
import google.generativeai as genai
from PIL import Image
import time
from datetime import datetime

# ================= 1. 全局配置 =================
st.set_page_config(
    page_title="一叶摇风 | 影像私教", 
    page_icon="🍃", 
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ================= 2. 登录验证系统 (带有效期控制) =================
def check_login():
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
        st.session_state.user_phone = None
        st.session_state.expire_date = None

    if st.session_state.logged_in:
        return True

    # --- 布局：左海报，右登录 ---
    col_poster, col_login = st.columns([1.2, 1])
    
    with col_poster:
        st.image("https://images.unsplash.com/photo-1516035069371-29a1b244cc32?q=80&w=1000&auto=format&fit=crop", 
                 caption="Capture the moment. Analyze the soul.", 
                 use_container_width=True)

    with col_login:
        st.markdown("<br>", unsafe_allow_html=True)
        st.title("🍃 一叶摇风影像")
        
        # === ✨ 新增：产品功能简介 ===
        st.info("""
        **您的 24小时 AI 摄影私教**
        
        📸 **一键上传**：支持相册图片或现场拍摄。
        📊 **修图参数**：直接给出醒图/Lightroom 具体数值 (如: 曝光+10)。
        🎓 **拍摄指导**：大师级构图与光影分析建议。
        """)
        
        st.divider()
        
        # === 登录卡片 ===
        with st.container(border=True):
            st.subheader("🔐 会员登录")
            phone_input = st.text_input("手机号码", placeholder="请输入您的手机号", max_chars=11)
            code_input = st.text_input("激活码", placeholder="请输入您的专属 Key", type="password")
            
            if st.button("立即登录 / Login", type="primary", use_container_width=True):
                # 1. 基础校验
                if len(phone_input) != 11:
                    st.error("请输入 11 位手机号码")
                    return False
                
                # 2. 读取后台数据
                try:
                    # 格式升级为：["手机号:激活码:到期日期"]
                    valid_accounts = st.secrets["VALID_ACCOUNTS"]
                except:
                    st.error("系统配置维护中")
                    return False

                # 3. 核心验证逻辑
                login_success = False
                expire_date_str = ""
                
                # 遍历后台列表进行匹配
                for account_str in valid_accounts:
                    try:
                        # 解析字符串 "手机:码:日期"
                        parts = account_str.split(":")
                        if len(parts) == 3:
                            db_phone = parts[0].strip()
                            db_code = parts[1].strip()
                            db_date = parts[2].strip()
                            
                            # 匹配手机和密码
                            if phone_input == db_phone and code_input == db_code:
                                # 检查是否过期
                                exp_date = datetime.strptime(db_date, "%Y-%m-%d")
                                now_date = datetime.now()
                                
                                if now_date > exp_date:
                                    st.error(f"❌ 您的会员已于 {db_date} 到期，请联系微信续费。")
                                    return False
                                else:
                                    login_success = True
                                    expire_date_str = db_date
                                    break
                    except:
                        continue # 跳过格式错误的行

                if login_success:
                    st.session_state.logged_in = True
                    st.session_state.user_phone = phone_input
                    st.session_state.expire_date = expire_date_str
                    print(f"✅ LOGIN: [{phone_input}] Exp:{expire_date_str}")
                    st.success(f"验证通过！有效期至：{expire_date_str}")
                    time.sleep(0.8)
                    st.rerun()
                else:
                    st.error("登录失败：账号密码错误，或未授权。")
                    return False

        # === 购买与安装 ===
        st.caption("💎 购买会员/续费请联系微信：**BayernGomez**")
        with st.expander("📲 如何安装到手机桌面？"):
            st.markdown("""
            **iPhone:** Safari 打开 -> 分享按钮 -> 添加到主屏幕
            **Android:** Chrome 打开 -> 菜单 -> 添加到主屏幕
            """)
    
    return False

# ================= 3. 主程序逻辑 =================
def main_app():
    # 读取 Key
    try:
        api_key = st.secrets["GOOGLE_API_KEY"]
        genai.configure(api_key=api_key)
    except:
        st.error("API Key 缺失")
        st.stop()

    # 提示词
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
        # 显示有效期
        if st.session_state.expire_date:
            st.caption(f"📅 有效期至: {st.session_state.expire_date}")
            
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