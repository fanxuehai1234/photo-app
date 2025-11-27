import streamlit as st
import google.generativeai as genai
from PIL import Image

# 1. 页面设置
st.set_page_config(page_title="BayernGomez 修图大师", page_icon="🎨")

# 2. 自动读取 Key
try:
    api_key = st.secrets["GOOGLE_API_KEY"]
except:
    st.error("⚠️ 错误：请在 Streamlit 后台配置 GOOGLE_API_KEY。")
    st.stop()

# 3. 核心提示词
SYSTEM_PROMPT = """
你是一位专业的修图大师 BayernGomez。
请从构图、光影、色彩情感等方面分析用户上传的照片。
并给出具体的后期修图参数建议（例如：高光-10，阴影+20，色温变暖）。
如果用户有特殊要求，请优先满足。
"""

def main():
    with st.sidebar:
        st.success("✅ 云端大脑已连接")
        st.info("无需翻墙 · 国内直连可用")
        
        # === 升级模型列表 ===
        # 这里我们换上了目前真正最强的 2.0 和 1.5 Pro
        model_name = st.selectbox("选择大脑", [
            "gemini-2.0-flash-exp (最新 v2.0)", 
            "gemini-1.5-pro (最强 v1.5)",
            "gemini-1.5-flash (极速 v1.5)"
        ])
        
        # 映射逻辑
        if "2.0" in model_name:
            real_model_name = "gemini-2.0-flash-exp"
        elif "pro" in model_name:
            real_model_name = "gemini-1.5-pro"
        else:
            real_model_name = "gemini-1.5-flash"
        # ===================

    st.title("🎨 BayernGomez 智能修图大师")
    st.write("上传照片，AI 帮您分析修图思路！")

    uploaded_file = st.file_uploader("点击上传照片...", type=["jpg", "jpeg", "png"])

    if uploaded_file:
        image = Image.open(uploaded_file)
        st.image(image, caption='预览', use_container_width=True)
        
        user_req = st.text_input("有什么特殊需求？(例如：日系小清新)")

        if st.button("🚀 开始智能分析"):
            try:
                with st.spinner(f'🤖 正在使用 {real_model_name} 思考中...'):
                    genai.configure(api_key=api_key)
                    model = genai.GenerativeModel(model_name=real_model_name, system_instruction=SYSTEM_PROMPT)
                    
                    prompt = "请分析这张图片。"
                    if user_req: prompt += f" 用户需求：{user_req}"
                    
                    response = model.generate_content([prompt, image])
                    st.success("✅ 分析完成！")
                    st.markdown(response.text)
            except Exception as e:
                # 如果 2.0 报错，通常是因为版本太新，提示用户
                if "404" in str(e):
                    st.error("出错啦！可能是 2.0 模型还在测试中，请在左侧切换回 1.5-pro 试试。")
                else:
                    st.error(f"出错了：{e}")

if __name__ == "__main__":
    main()