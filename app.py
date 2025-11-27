import streamlit as st
import google.generativeai as genai
from PIL import Image

# 1. 页面配置
st.set_page_config(page_title="BayernGomez 修图大师", page_icon="🎨")

# 2. 核心提示词
SYSTEM_PROMPT = """
你是一位专业的修图大师 BayernGomez。
请从构图、光影、色彩情感等方面分析用户上传的照片。
并给出具体的后期修图参数建议（例如：高光-10，阴影+20，色温变暖）。
如果用户有特殊要求，请优先满足。
"""

def main():
    # 侧边栏
    with st.sidebar:
        st.header("⚙️ 设置")
        api_key = st.text_input("请输入 Google API Key", type="password")
        st.markdown("[👉 获取 API Key](https://aistudio.google.com/app/apikey)")
        model = st.selectbox("选择模型", ["gemini-1.5-flash", "gemini-1.5-pro"])
        st.info("提示：请确保 VPN 已开启 (美国/日本节点)。")

    # 主界面
    st.title("🎨 BayernGomez 智能修图大师")
    st.write("上传照片，AI 帮您分析修图思路！")

    uploaded_file = st.file_uploader("选择一张照片...", type=["jpg", "jpeg", "png"])

    if uploaded_file:
        image = Image.open(uploaded_file)
        st.image(image, caption='预览', use_container_width=True)
        user_req = st.text_input("您想要什么风格？(例如：日系小清新)")

        if st.button("🚀 开始分析"):
            if not api_key:
                st.error("❌ 请先在左侧填入 API Key！")
            else:
                try:
                    with st.spinner('🤖 AI 正在思考中...'):
                        genai.configure(api_key=api_key)
                        model_instance = genai.GenerativeModel(model_name=model, system_instruction=SYSTEM_PROMPT)
                        prompt = "请分析这张图片。"
                        if user_req: prompt += f" 用户需求：{user_req}"
                        response = model_instance.generate_content([prompt, image])
                        st.success("✅ 分析完成！")
                        st.markdown(response.text)
                except Exception as e:
                    st.error(f"出错了：{e}")

if __name__ == "__main__":
    main()