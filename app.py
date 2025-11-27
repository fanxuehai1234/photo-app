import streamlit as st
import google.generativeai as genai
import sys

st.set_page_config(page_title="故障诊断模式", page_icon="🛠️")
st.title("🛠️ BayernGomez 服务器诊断报告")

# 1. 检查 Key 是否存在
try:
    api_key = st.secrets["GOOGLE_API_KEY"]
    st.success("✅ 1. API Key 已从云端读取")
except:
    st.error("❌ 1. 未检测到 Key！请检查 Secrets 设置")
    st.stop()

# 2. 检查工具包版本
st.write("---")
st.subheader("2. 环境版本检查")
st.write(f"- **Python 版本:** `{sys.version.split()[0]}`")
try:
    lib_version = genai.__version__
    st.write(f"- **Google工具包版本:** `{lib_version}`")
    
    # 判断版本是否达标
    ver_parts = lib_version.split('.')
    if int(ver_parts[1]) >= 6: # 检查是否大于 0.6
        st.success("✅ 工具包版本合格 (支持 1.5 Flash)")
    else:
        st.error(f"❌ 工具包版本太旧 ({lib_version})！这就是报错的原因！")
except Exception as e:
    st.error(f"❌ 无法检测版本: {e}")

# 3. 检查您的 Key 能看到哪些模型
st.write("---")
st.subheader("3. 账号权限检查 (列出所有可用模型)")

if st.button("🔍 点击扫描可用模型"):
    try:
        genai.configure(api_key=api_key)
        models = list(genai.list_models())
        
        found_flash = False
        st.write("您的 Key 可以调用以下模型：")
        
        # 遍历打印
        for m in models:
            if "generateContent" in m.supported_generation_methods:
                st.code(m.name) # 显示模型真实名字
                if "gemini-1.5-flash" in m.name:
                    found_flash = True
        
        st.write("---")
        if found_flash:
            st.success("✅ 诊断结果：您的账号拥有 1.5 Flash 权限！")
            st.info("如果这里显示有权限但之前报错，说明是代码写法问题。")
        else:
            st.error("❌ 诊断结果：您的账号里找不到 1.5 Flash！")
            st.warning("可能原因：\n1. 您的 Google Cloud 项目没有开启相关权限。\n2. 您的 API Key 创建时选错了项目。\n3. Google 对您的地区进行了限制。")
            
    except Exception as e:
        st.error(f"❌ 扫描失败，原因：{e}")