import streamlit as st
import google.generativeai as genai
from PIL import Image

# ================= 1. 全局配置 =================
st.set_page_config(
    page_title="一叶摇风 | 影像私教", 
    page_icon="🍃", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# 读取 Key
try:
    api_key = st.secrets["GOOGLE_API_KEY"]
    genai.configure(api_key=api_key)
except:
    st.error("⚠️ 请在 Streamlit 后台 Secrets 配置 GOOGLE_API_KEY")
    st.stop()

# ================= 2. 定义双重人设 (日常 vs 专业) =================

# 日常模式提示词 (轻松、快速、发朋友圈)
PROMPT_DAILY = """
你是一位亲切的摄影博主“一叶摇风”。
用户上传了一张生活照片，请用轻松、鼓励的口吻进行点评。
重点关注：
1. 这张照片好在哪里？(夸奖)
2. 怎么修图能发朋友圈？(简单的滤镜或参数建议)
3. 拍照小贴士。(简短建议)
请用 Markdown 格式，不用太长，通俗易懂。
"""

# 专业模式提示词 (深度、艺术、商业级)
PROMPT_PRO = """
你是一位享誉国际的视觉艺术总监“一叶摇风”。
用户上传了一张摄影作品，请从专业美学角度进行深度拆解。

请严格按照以下结构输出报告：

### 👁️ 视觉透视 (Visual Analysis)
* **构图语言:** (分析线条、透视、视觉重心)
* **光影层次:** (分析光质、明暗对比、影调风格)
* **色彩情绪:** (分析配色方案、色彩心理学)

### 🎨 商业级修图方案 (Post-Processing)
*请给出具体的 Lightroom / Capture One 调整思路：*
* **影调重塑:** (如：S型曲线调整，高光压缩...)
* **色彩分级 (Color Grading):** (如：阴影偏青，高光偏橙，分离色调...)
* **质感强化:** (如：清晰度、去朦胧、颗粒感的具体数值建议)

### 🎓 大师进阶课 (Master Class)
* 如果这张照片要拿去参赛或商用，前期拍摄时还可以如何极致优化？(从焦段选择、布光、模特情绪引导等方面给出建议)

---
**总监评分:** {分数}/10
"""

# ================= 3. 主程序 =================
def main():
    # --- 侧边栏设置 ---
    with st.sidebar:
        st.title("🍃 引擎设置")
        st.info("欢迎来到一叶摇风影像工作室。")
        
        # 模式选择 (核心修改)
        mode = st.radio(
            "选择分析模式:", 
            ["📷 日常快评 (Daily)", "🧐 专业以此 (Professional)"],
            captions=[
                "模型: Gemini 2.0 Flash Lite | 速度快，适合生活照", 
                "模型: Gemini 2.5 Flash | 能力强，适合精修/创作"
            ]
        )
        
        # 根据模式配置模型和提示词
        if "Daily" in mode:
            # 日常模式：用 2.0 Flash Lite (极速，高额度)
            real_model = "gemini-2.0-flash-lite-preview-02-05"
            active_prompt = PROMPT_DAILY
            btn_label = "🚀 开始快速评估"
        else:
            # 专业模式：用 2.5 Flash (目前您账号里最强的 Flash，高额度)
            real_model = "gemini-2.5-flash"
            active_prompt = PROMPT_PRO
            btn_label = "💎 开始深度解析"
            
        st.divider()
        st.caption(f"当前内核: `{real_model}`\n状态: 🟢 在线 | 额度: 无限(Free)")

    # --- 主界面 ---
    st.title("🍃 一叶摇风 | 影像私教")
    
    # 动态副标题
    if "Daily" in mode:
        st.markdown("### 记录生活，发现美好。")
    else:
        st.markdown("### 极致影像，深度解构。")

    # 标签页
    tab1, tab2 = st.tabs(["📂 上传文件", "📷 拍摄现场"])
    image_data = None

    with tab1:
        uploaded_file = st.file_uploader("支持 JPG / PNG / WEBP", type=["jpg", "jpeg", "png", "webp"])
        if uploaded_file:
            image_data = Image.open(uploaded_file)

    with tab2:
        camera_file = st.camera_input("点击拍摄")
        if camera_file:
            image_data = Image.open(camera_file)

    # --- 处理逻辑 ---
    if image_data:
        st.divider()
        col1, col2 = st.columns([1, 1.2])
        
        with col1:
            st.image(image_data, caption="原始影像", use_container_width=True)
        
        with col2:
            st.subheader("💡 导师反馈")
            user_input = st.text_input("您的想法 (可选):", placeholder="例如：我想修出电影感...")
            
            if st.button(btn_label, type="primary", use_container_width=True):
                try:
                    # 动态显示状态
                    status_text = "✨ 正在快速浏览..." if "Daily" in mode else "🧠 正在进行深度美学分析..."
                    
                    with st.status(status_text, expanded=True) as status:
                        st.write("正在连接 Google 影像大脑...")
                        
                        genai.configure(api_key=api_key)
                        model = genai.GenerativeModel(real_model, system_instruction=active_prompt)
                        
                        req = "请分析这张图片。"
                        if user_input: req += f" 用户备注：{user_input}"
                        
                        st.write("正在生成报告...")
                        response = model.generate_content([req, image_data])
                        
                        status.update(label="✅ 分析完成", state="complete", expanded=False)
                    
                    st.markdown(response.text)
                    
                except Exception as e:
                    st.error("分析中断")
                    err_msg = str(e)
                    if "404" in err_msg:
                        st.warning(f"错误：您的账号暂不支持模型 {real_model}，请切换回另一种模式试试。")
                    elif "429" in err_msg:
                        st.warning("提示：当前使用人数过多，请稍等1分钟再试。")
                    else:
                        st.warning(f"详细错误：{err_msg}")

if __name__ == "__main__":
    main()