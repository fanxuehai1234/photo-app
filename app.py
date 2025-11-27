import streamlit as st
import google.generativeai as genai
from PIL import Image
import io

# 页面配置
st.set_page_config(page_title="BayernGomez 修图 V3", page_icon="🎨", layout="wide")

# 读取 Key
try:
    api_key = st.secrets["GOOGLE_API_KEY"]
    genai.configure(api_key=api_key)
except:
    st.error("⚠️ 未配置 API Key！")
    st.stop()

def main():
    # 标题带 V3，证明更新成功
    st.title("🎨 BayernGomez 智能修图大师 V3 (尝试出图版)")
    
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("1. 上传与需求")
        uploaded_file = st.file_uploader("上传照片...", type=["jpg", "png"])
        user_req = st.text_input("请输入需求 (例如：换成牛仔裤)")
        
        # 强制使用 Imagen 模型
        start_btn = st.button("🚀 开始生成效果图", type="primary")

    if uploaded_file and start_btn:
        image = Image.open(uploaded_file)
        with col1:
            st.image(image, caption="原图", use_container_width=True)
        
        with col2:
            st.subheader("2. 处理结果")
            
            # 1. 先用 Gemini 分析图片内容
            status = st.status("正在分析原图内容...", expanded=True)
            try:
                vision_model = genai.GenerativeModel('gemini-1.5-flash')
                description = vision_model.generate_content(["请详细描述这张图片的主体、姿势、环境，50字以内。", image]).text
                status.write(f"原图识别：{description}")
                
                # 2. 尝试调用 Imagen 3 画图
                status.update(label="正在尝试生成新图片 (Imagen 3)...", state="running")
                
                # 构造绘画提示词
                prompt = f"High quality photo. {description}. Modifiction: {user_req}. Photorealistic, 8k."
                
                # === 关键：调用生图模型 ===
                # 注意：如果您的 Key 没权限，这里会直接报错
                painter = genai.ImageGenerationModel("imagen-3.0-generate-001")
                
                result = painter.generate_images(
                    prompt=prompt,
                    number_of_images=1,
                    aspect_ratio="3:4",
                    safety_filter="block_only_high"
                )
                
                # 显示图片
                status.update(label="✅ 生成成功！", state="complete")
                
                for img in result.images:
                    img_pil = Image.open(io.BytesIO(img._image_bytes))
                    st.image(img_pil, caption=f"AI 生成的效果图 (根据：{user_req})", use_container_width=True)
                    
            except Exception as e:
                status.update(label="❌ 生成失败", state="error")
                st.error("无法生成图片，原因如下：")
                
                error_msg = str(e)
                if "404" in error_msg or "Not Found" in error_msg:
                    st.warning("核心原因：您的免费 API Key 没有权限调用谷歌的 'Imagen 3' 画图模型。")
                    st.info("解释：Google AI Studio 的画图功能目前仅对部分账号开放，或者只在网页版沙盒里可用，API 还没完全开放给免费用户。")
                elif "403" in error_msg:
                     st.warning("核心原因：权限被拒绝 (403)。您的账号所在地区或类型不支持生图。")
                else:
                    st.code(error_msg)
                
                st.write("---")
                st.caption("虽然无法出图，但 Gemini 依然可以提供修图建议：")
                # 兜底：如果画不出图，至少给个建议
                advice_model = genai.GenerativeModel('gemini-1.5-flash')
                advice = advice_model.generate_content([f"用户想把这张图：{user_req}，请给出PS修图步骤。", image]).text
                st.markdown(advice)

if __name__ == "__main__":
    main()