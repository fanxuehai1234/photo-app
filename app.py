import streamlit as st
import google.generativeai as genai
from PIL import Image

# 1. 页面设置
st.set_page_config(page_title="BayernGomez 修图大师", page_icon="🎨")

# 2. 读取 Key
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
        
        # === 关键修改：使用您账号里真实存在的模型 ===
        model_label = st.selectbox("选择大脑", [
            "Gemini 2.0 Flash Lite (极速·高额度)", 
            "Gemini 2.0 Pro (超强·画质好)",
            "Gemini 2.5 Flash (神秘新版)"
        ])
        
        # === 映射到您截图里的真实代码 ===
        if "Lite" in model_label:
            # 这是您截图里有的模型，速度最快，额度通常最高
            real_model_name = "gemini-2.0-flash-lite-preview-02-05"
        elif "Pro" in model_label:
            # 2.0 Pro 版本
            real_model_name = "gemini-2.0-pro-exp-02-05"
        else:
            # 您截图里的 2.5 版本
            real_model_name = "gemini-2.5-flash"
        
        st.caption(f"当前调用内核: `{real_model_name}`")

    st.title("🎨 BayernGomez 智能修图大师")
    st.write("已启用 Google 最新一代 2.0/2.5 模型！")

    uploaded_file = st.file_uploader("点击上传照片...", type=["jpg", "jpeg", "png"])

    if uploaded_file:
        try:
            image = Image.open(uploaded_file)
            st.image(image, caption='预览', use_container_width=True)
            
            user_req = st.text_input("有什么特殊需求？(例如：日系小清新)")

            if st.button("🚀 开始智能分析", key="run_btn"):
                try:
                    with st.spinner(f'🤖 {model_label} 正在思考中...'):
                        genai.configure(api_key=api_key)
                        model = genai.GenerativeModel(model_name=real_model_name, system_instruction=SYSTEM_PROMPT)
                        
                        prompt = "请分析这张图片。"
                        if user_req: prompt += f" 用户需求：{user_req}"
                        
                        response = model.generate_content([prompt, image])
                        st.success("✅ 分析完成！")
                        st.markdown(response.text)
                except Exception as e:
                    st.error("❌ 调用失败")
                    st.warning(f"错误信息：{e}")
                    if "404" in str(e):
                        st.info("提示：如果报404，请在左侧切换另一个模型试试。")
                    elif "429" in str(e):
                        st.info("提示：当前模型额度已满，请切换到 'Flash Lite' 试试。")
        except Exception as img_err:
            st.error(f"图片读取失败: {img_err}")

if __name__ == "__main__":
    main()