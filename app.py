import streamlit as st
import google.generativeai as genai
from PIL import Image

# 1. 页面基础设置
st.set_page_config(page_title="BayernGomez 修图大师", page_icon="🎨")

# 2. 自动读取 Key
try:
    api_key = st.secrets["GOOGLE_API_KEY"]
except:
    st.error("⚠️ 严重错误：未检测到 Key！请在 Streamlit 后台 Settings -> Secrets 中配置。")
    st.stop()

# 3. 核心提示词
SYSTEM_PROMPT = """
你是一位专业的修图大师 BayernGomez。
请从构图、光影、色彩情感等方面分析用户上传的照片。
并给出具体的后期修图参数建议（例如：高光-10，阴影+20，色温变暖）。
如果用户有特殊要求，请优先满足。
"""

def main():
    # --- 侧边栏设置 ---
    with st.sidebar:
        st.success("✅ 云端大脑已连接")
        st.info("无需翻墙 · 国内直连可用")
        
        # 只保留两个最稳定的 1.5 模型
        model_option = st.selectbox("选择大脑", [
            "gemini-1.5-flash (极速版 - 推荐)", 
            "gemini-1.5-pro (增强版 - 更聪明)"
        ])
        
        # 转换模型名称
        if "pro" in model_option:
            real_model_name = "gemini-1.5-pro"
        else:
            real_model_name = "gemini-1.5-flash"

    # --- 主界面 ---
    st.title("🎨 BayernGomez 智能修图大师")
    st.markdown("上传照片，AI 帮您分析修图思路！")

    # 上传组件
    uploaded_file = st.file_uploader("点击上传照片...", type=["jpg", "jpeg", "png"])

    if uploaded_file:
        # 显示图片
        try:
            image = Image.open(uploaded_file)
            st.image(image, caption='预览', use_container_width=True)
            
            # 用户需求输入
            user_req = st.text_input("有什么特殊需求？(例如：日系小清新)")

            # 按钮 (加了 key 防止报错)
            if st.button("🚀 开始智能分析", key="run_btn"):
                try:
                    with st.spinner('🤖 AI 正在思考中...'):
                        # 配置 Key
                        genai.configure(api_key=api_key)
                        
                        # 初始化模型
                        model = genai.GenerativeModel(model_name=real_model_name, system_instruction=SYSTEM_PROMPT)
                        
                        # 准备提示词
                        prompt = "请分析这张图片。"
                        if user_req: prompt += f" 用户需求：{user_req}"
                        
                        # 发送请求
                        response = model.generate_content([prompt, image])
                        
                        # 显示结果
                        st.success("✅ 分析完成！")
                        st.markdown(response.text)
                        
                except Exception as e:
                    st.error("❌ 分析失败")
                    # 智能判断错误类型
                    err_msg = str(e)
                    if "429" in err_msg or "Quota" in err_msg:
                        st.warning("原因：免费额度已用完 (429 Error)。请明天再试，或切换回 '1.5-flash' 模型。")
                    else:
                        st.warning(f"详细错误信息：{err_msg}")
        except Exception as img_error:
            st.error(f"图片加载失败，请换一张图试试。错误：{img_error}")

if __name__ == "__main__":
    main()