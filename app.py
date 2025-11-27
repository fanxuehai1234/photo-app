import streamlit as st
import google.generativeai as genai
from PIL import Image

# ================= 1. 全局配置 =================
st.set_page_config(
    page_title="BayernGomez 影像私教", 
    page_icon="📸", 
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

# 定义专业的摄影导师提示词
SYSTEM_PROMPT = """
你是一位拥有20年经验的顶级摄影师和后期讲师 "BayernGomez"。
用户的需求是：上传一张照片，希望得到你的专业点评、修图建议和拍摄指导。

请严格按照以下 Markdown 格式输出分析报告：

### 📸 综合评分: {分数}/10
> 用一句话犀利地点评这张照片的整体感觉。

### ✨ 亮点分析
* **构图:** ...
* **光影:** ...
* **氛围:** ...

### 🎨 后期修图指南 (Lightroom/醒图参数)
*请给出具体的调整方向，例如：*
* **曝光/对比度:** (例如：建议降低高光 -20，提亮阴影 +15...)
* **色彩 (HSL):** (例如：橙色饱和度 -10 让肤色更通透...)
* **质感/特效:** (例如：加一点颗粒感制造胶片味...)

### 🎓 下次拍摄建议 (私教指导)
* **构图优化:** (如果重拍，怎么构图更好？)
* **光线运用:** (什么时间或角度拍更好？)
* **模特引导:** (如果是人像，姿势怎么摆更自然？)

---
**导师寄语:** 给摄影师一句鼓励的话。
"""

# ================= 2. 界面设计 =================
def main():
    # 侧边栏
    with st.sidebar:
        st.title("📸 设置与说明")
        st.info("欢迎使用 BayernGomez 影像私教。上传照片，获取专业级摄影反馈。")
        
        # 模型选择 (默认用最稳的 Flash)
        model_type = st.radio(
            "选择私教级别:", 
            ["Gemini 1.5 Flash (极速·免费)", "Gemini 1.5 Pro (专家·深度)"],
            captions=["响应快，适合日常打卡", "思考深，适合精修作品"]
        )
        
        # 映射模型名
        real_model = "gemini-1.5-pro" if "Pro" in model_type else "gemini-1.5-flash"
        
        st.divider()
        st.caption("Designed by BayernGomez")

    # 主标题区
    st.title("📸 BayernGomez 影像私教")
    st.markdown("### 您的随身摄影导师，让每一张照片更出色。")

    # === 核心交互区：标签页切换 ===
    tab1, tab2 = st.tabs(["📂 相册上传 (文件)", "📷 现场拍摄 (相机)"])
    
    image_data = None

    # Tab 1: 文件上传
    with tab1:
        uploaded_file = st.file_uploader("拖入或选择照片 (JPG/PNG)", type=["jpg", "jpeg", "png"])
        if uploaded_file:
            image_data = Image.open(uploaded_file)

    # Tab 2: 调用摄像头
    with tab2:
        camera_file = st.camera_input("点击拍摄")
        if camera_file:
            image_data = Image.open(camera_file)

    # === 如果有图，显示分析界面 ===
    if image_data:
        st.divider()
        
        # 左右分栏：左图右文
        col_img, col_text = st.columns([1, 1.2])
        
        with col_img:
            st.image(image_data, caption="待分析的影像", use_container_width=True)
        
        with col_text:
            st.subheader("💡 导师视角")
            user_input = st.text_area("您想问导师什么？(可选)", placeholder="例如：我觉得这张脸太黑了，怎么救？或者我想修成日系风格。")
            
            # 提交按钮
            if st.button("🚀 开始专业评估", type="primary", use_container_width=True):
                try:
                    with st.status("🧠 导师正在分析构图与光影...", expanded=True) as status:
                        st.write("正在读取影像信息...")
                        # 调用模型
                        model = genai.GenerativeModel(real_model, system_instruction=SYSTEM_PROMPT)
                        
                        req_text = "请评估这张照片。"
                        if user_input:
                            req_text += f" 我的具体困惑是：{user_input}"
                        
                        st.write("正在生成修图方案...")
                        response = model.generate_content([req_text, image_data])
                        
                        status.update(label="✅ 评估报告已生成", state="complete", expanded=False)
                    
                    # 输出结果
                    st.markdown(response.text)
                    
                except Exception as e:
                    st.error(f"分析中断: {e}")
                    if "429" in str(e):
                        st.warning("提示：今日免费咨询次数已达上限，请明天再来。")

if __name__ == "__main__":
    main()