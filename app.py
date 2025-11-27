import streamlit as st
import google.generativeai as genai
from PIL import Image

# ================= 1. 全局配置 =================
st.set_page_config(
    page_title="一叶摇风影像私教", 
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

# 定义“一叶摇风”的导师人设
SYSTEM_PROMPT = """
你是一位资深摄影导师“一叶摇风”。
你的风格：专业、细腻、富有艺术感。
用户的需求是：上传一张照片，希望得到你的专业点评、修图建议和拍摄指导。

请严格按照以下 Markdown 格式输出分析报告：

### 🌿 影像评分: {分数}/10
> 用一句富有艺术感的话点评这张照片的意境。

### ✨ 亮点解析
* **构图:** ...
* **光影:** ...
* **色彩:** ...

### 🎨 后期修图指南 (一叶摇风·调色思路)
*请给出具体的调整方向，例如：*
* **曝光/对比度:** (例如：建议降低高光 -20，让画面更柔和...)
* **色彩 (HSL):** (例如：橙色饱和度 -10 让肤色更通透...)
* **氛围感:** (例如：加一点颗粒感制造胶片味...)

### 🎓 拍摄进阶指导
* **构图优化:** (如果重拍，怎么构图更好？)
* **光线运用:** (什么时间或角度拍更好？)

---
**一叶摇风寄语:** 给摄影师一句鼓励的话。
"""

# ================= 2. 界面设计 =================
def main():
    # 侧边栏
    with st.sidebar:
        st.title("🍃 设置")
        st.info("欢迎来到「一叶摇风」影像工作室。")
        
        # === 关键修改：只使用您账号里有的模型 ===
        model_label = st.radio(
            "选择私教引擎:", 
            ["Gemini 2.0 Flash Lite (极速)", "Gemini 2.5 Flash (最新)"],
            captions=["速度最快，额度高", "谷歌最新模型，更聪明"]
        )
        
        # 映射到真实模型名称 (根据您的诊断报告)
        if "2.5" in model_label:
            real_model = "gemini-2.5-flash"
        else:
            real_model = "gemini-2.0-flash-lite-preview-02-05"
            
        st.caption(f"当前内核: `{real_model}`")
        st.divider()

    # 主标题区
    st.title("🍃 一叶摇风 | 影像私教")
    st.markdown("### 上传照片，获取专业级摄影反馈与修图思路。")

    # === 核心交互区 ===
    tab1, tab2 = st.tabs(["📂 相册上传", "📷 现场拍摄"])
    
    image_data = None

    with tab1:
        uploaded_file = st.file_uploader("选择照片 (JPG/PNG)", type=["jpg", "jpeg", "png"])
        if uploaded_file:
            image_data = Image.open(uploaded_file)

    with tab2:
        camera_file = st.camera_input("点击拍摄")
        if camera_file:
            image_data = Image.open(camera_file)

    # === 分析逻辑 ===
    if image_data:
        st.divider()
        col_img, col_text = st.columns([1, 1.2])
        
        with col_img:
            st.image(image_data, caption="待分析影像", use_container_width=True)
        
        with col_text:
            st.subheader("💡 导师视角")
            user_input = st.text_area("您想问什么？(可选)", placeholder="例如：我想修成日系清新风格，或者觉得照片太暗了。")
            
            if st.button("🚀 开始专业评估", type="primary", use_container_width=True):
                try:
                    with st.status("🧠 一叶摇风正在分析...", expanded=True) as status:
                        st.write("正在读取影像信息...")
                        
                        # 调用模型
                        model = genai.GenerativeModel(real_model, system_instruction=SYSTEM_PROMPT)
                        
                        req_text = "请评估这张照片。"
                        if user_input:
                            req_text += f" 我的具体困惑是：{user_input}"
                        
                        st.write("正在生成修图方案...")
                        response = model.generate_content([req_text, image_data])
                        
                        status.update(label="✅ 评估报告已生成", state="complete", expanded=False)
                    
                    st.markdown(response.text)
                    
                except Exception as e:
                    st.error("分析中断")
                    # 智能报错提示
                    err_msg = str(e)
                    if "404" in err_msg:
                        st.warning(f"错误：找不到模型 {real_model}。请尝试切换另一个模型。")
                    elif "429" in err_msg:
                        st.warning("提示：当前模型使用人数过多或额度已满，请稍后再试。")
                    else:
                        st.warning(f"详细错误：{err_msg}")

if __name__ == "__main__":
    main()