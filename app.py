import streamlit as st
import google.generativeai as genai
from PIL import Image

# 1. 页面设置
st.set_page_config(page_title="BayernGomez 修图大师", page_icon="🎨")

# 2. 自动读取 Key (云端保险箱)
try:
    # 尝试从后台读取 Key
    api_key = st.secrets["GOOGLE_API_KEY"]
except:
    # 如果读取失败，就在网页上报错
    st.error("⚠️ 严重错误：未配置 API Key！请在 Streamlit 后台 Settings -> Secrets 中配置。")
    st.stop()

# 3. 核心提示词
SYSTEM_PROMPT = """
你是一位专业的修图大师 BayernGomez。
请从构图、光影、色彩情感等方面分析用户上传的照片。
并给出具体的后期修图参数建议（例如：高光-10，阴影+20，色温变暖）。
如果用户有特殊要求，请优先满足。
"""

def main():
    # --- 侧边栏 (无输入框版) ---
    with st.sidebar:
        st.success("✅ 云端大脑已连接")
        st.info("无需翻墙 · 国内直连可用")
        
        # 只保留模型选择
        model_name = st.selectbox("选择大脑", ["gemini-1.5-flash (快)", "gemini-1.5-pro (强)"])
        real_model_name = "gemini-1.5-flash" if "flash" in model_name else "gemini-1.5-pro"

    # --- 主界面 ---
    st.title("🎨 BayernGomez 智能修图大师")
    st.write("上传照片，AI 帮您分析修图思路！")

    uploaded_file = st.file_uploader("点击上传照片...", type=["jpg", "jpeg", "png"])

    if uploaded_file:
        image = Image.open(uploaded_file)
        st.image(image, caption='预览', use_container_width=True)
        
        user_req = st.text_input("有什么特殊需求？(例如：日系小清新)")

        if st.button("🚀 开始智能分析"):
            try:
                with st.spinner('🤖 AI 正在云端思考...'):
                    # 自动注入 Key
                    genai.configure(api_key=api_key)
                    
                    model = genai.GenerativeModel(model_name=real_model_name, system_instruction=SYSTEM_PROMPT)
                    
                    prompt = "请分析这张图片。"
                    if user_req: prompt += f" 用户需求：{user_req}"
                    
                    response = model.generate_content([prompt, image])
                    
                    st.success("✅ 分析完成！")
                    st.markdown(response.text)
            except Exception as e:
                st.error(f"出错了：{e}")

if __name__ == "__main__":
    main()