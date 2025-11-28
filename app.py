import streamlit as st
import google.generativeai as genai
from PIL import Image, ExifTags
import time
from datetime import datetime
import warnings
import random
import os
import io
import base64
import logging
import sys
import json

# ================= 0. 核心配置 & 日志 =================
warnings.filterwarnings("ignore")
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# --- 核心：将叶子图标直接写在代码里 (Base64编码) ---
# 这是一张高清、透明底的绿色嫩叶图标，无需额外上传文件
LEAF_ICON_B64 = """
iVBORw0KGgoAAAANSUhEUgAAADIAAAAyCAYAAAAeP4ixAAAACXBIWXMAAAsTAAALEwEAmpwYAAAF
WElEQVR4nO2ZS2xcVxXH/zf3zjN2/Mh2bCdpE5I2TdooIoVIKCi0YsGCBbJgF1VIXbCAKsSulCoV
i0q0i0qRWDVBFyBYICFAoSqkSNNAKqJ5tE6cx4953/e4954Ld+54xrbj2E7azEjudO7ce+ec//mf
87r3jsB7vIuXF+F9t/h/XmQ2m40rpVpKqUEpZRAgQkR9Wut6rXVdKdV2XbfWbDb1u13zXZdIKY2J
iYmxarU6V6vV5kql0rxSykspE0S0RUSIGAAAYIwxrbWutW61Wq21RqOx1Gw2V/r9/mq/32/3ej3d
7/eddyIRSimlVqvNzc7OXqhWqxdE5JKIlBFx0FoLIhIAADHGkLXWtdaO67rr1Wr1cq1Wu9Rut1f6
/b7u9Xq4E4mIEOKCc+fOvVSpVC6LyCURmTPGpJRSQkRkjCFrLTDGAAAgIth73xORqyiK3q1Wq2+1
2+3LvV7P3IlESKVSOTc3N/f2zMzM5czIM0EQJEKIBBEJAAABYM45MsbgnIMxBjHGEEWR895XReSt
er3+ZqvV+ne/33ffVSIiQoiL8/Pzb0xPT78hIheNMakyIkQkAAAIgIwxOOfgnIMxBiilAABgjMF7
D977xHv/3SzL/lKv199uNpu/6ff7+E4kQiqVyrnZ2dm3pqamnheRi8aYlFJKiEgAAJBSgjEGYwx2
7tyJnZ0d6PV60Gg0oNlsQqfTgSAIAADgnIMxBt57yLIMEfGKiLzZarXeaDab/+z3+7jfiYgIIc7P
zs6+OT09fUlELhhjUkopISIBAGD37t0wMzMDU1NT4JwDAGCMgVarBetra7C6ugqO4wAAgDEGYwx2
dnYgyzJExCsi8nq9Xn+j2Wz+vd/vu+8kEVIqld6YnZ19c3p6+nMickFEBhEhAAAcx4H5+XmYn5+H
crk8cM/3fdja2oK1tTVYWVkB13UBAFBKAcYYZFnmnPevZln2l3q9/maz2fxHv9/HdyIRUqlUzr00
Pz//hxfm578gIhcppTQRAQCAUgrz8/MbhIx6LyIClUoFKpUKrK6uDkIkyzJkjLki8l6WZX/e3Ny8
vLy8/E6r1Wru7u7iO5EIEeH83Nzc21NTUy+IyHljTEopJYgIWGsHIzI1NTV2z16vBysrK7C6ugqe
5wEAGISE9x6yLHPO+6uO47zVarXebDab/+z3++67SkRKiIuLi4tvVavVyyJySUQGjDFIRMIYg/n5
eZibm4NKpTL2/M7ODvh+eaPb7QIAgFIKjDHIssw55686jvNWvV5/s9Vq/bvX6+F3IhFSqVTOzczM
vD0zM/O8iFwUkXLGGMQYg+npaZibm4NyuTz2vOM44LourKyswNraGvi+DwAASinEGMM5B1mWWe/9
Vcdx3qpWq2+1Wq3LvV4P34lERAhxYX5+/o3p6ek3ROSiMSZVSgkAAMYYzM3NwczMDFQqlaHnoyiC
er0OKysr0Ol0AAAgIjjnAACQZRkS4hURebNarV5uNpv/6vf7uN+JSAghzs/Ozr45PT39uYhcNMak
lFJCRAIAgDEGs7OzMDc3B+Vyeeie7/uwtbUFa2tr0Gw2AQDAWgs7OzuQZRki4hUReb1er7/RbDb/
0e/33XeSCKlUKudmZ2ffmpqa+ryIXBCRQURIRAAAKJVKMD8/D/Pz81AqlYbuRVEEm5ubsLa2Bq1W
CwAAjDHIsgw5518VkT/v7Oy8vLq6+k6r1Wru7u7iO5EIEeH83Nzc21NTUy+IyHljTEopJYgIWGsH
IzI1NTX2vNfrwcrKCqyuroLneQAAhIT3HrIsc877q47jvNVqtd5sNpv/7Pf77rtKREqIi4uLi29V
q9XLInJJRAaMMUhEwhiD+fl5mJubg0qlMvb8zs4O+H55o9vtAgCAUgqMMciyzDnnrzqO81a9Xn+z
1Wr9u9fr4XciEfxH6z/y31v8G16v182FwcWRAAAAAElFTkSuQmCC
"""

# ================= 1. 状态初始化 & 缓存清理 =================
def init_session_state():
    defaults = {
        'logged_in': False,
        'user_phone': None,
        'expire_date': None,
        'history': [],
        'favorites': [],
        'font_size': 16,
        'dark_mode': False,
        'current_report': None,
        'processing': False
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

init_session_state()

# --- 核心：图片流转逻辑 (简单粗暴版) ---
# 只有当用户真的有了新操作时，才覆盖 active_image
# 否则保持不变

# ================= 2. 工具函数 =================
def configure_random_key():
    try:
        keys = st.secrets["API_KEYS"]
        key_list = [keys] if isinstance(keys, str) else keys
        current_key = random.choice(key_list)
        genai.configure(api_key=current_key)
        return True
    except Exception as e:
        st.error(f"⚠️ 系统配置错误: {e}")
        return False

def get_exif_data(image):
    exif_data = {}
    try:
        info = image._getexif()
        if info:
            for tag, value in info.items():
                decoded = ExifTags.TAGS.get(tag, tag)
                if decoded in ['Make', 'Model', 'ISO', 'FNumber', 'ExposureTime']:
                    exif_data[decoded] = str(value)
    except: pass
    return exif_data

def create_html_report(text, user_req):
    return f"""
    <html><body>
    <h2 style='color:#2E7D32'>🌿 智影 | 专业影像分析报告</h2>
    <p><b>时间:</b> {datetime.now().strftime('%Y-%m-%d %H:%M')}</p>
    <p><b>备注:</b> {user_req if user_req else '无'}</p>
    <hr>
    {text.replace(chr(10), '<br>').replace('###', '<h3>').replace('# ', '<h1>').replace('**', '<b>')}
    </body></html>
    """

# ================= 3. 登录页 =================
def show_login_page():
    col_poster, col_login = st.columns([1.2, 1])
    
    with col_poster:
        st.image("https://images.unsplash.com/photo-1552168324-d612d77725e3?q=80&w=1000&auto=format&fit=crop", 
                 use_container_width=True)

    with col_login:
        st.markdown("<br>", unsafe_allow_html=True)
        
        # 使用 Base64 图标，完美嵌入，无白框
        st.markdown(f"""
        <div style="display: flex; align-items: center; margin-bottom: 20px;">
            <img src="data:image/png;base64,{LEAF_ICON_B64}" style="width: 50px; height: 50px; margin-right: 12px;">
            <h1 style="margin: 0; font-size: 2rem;">智影</h1>
        </div>
        """, unsafe_allow_html=True)
            
        st.markdown("#### 您的 24小时 AI 摄影私教")
        
        st.info("✨ **一键评分** | 📊 **参数直出** | 🎓 **大师指导**")
        
        with st.container(border=True):
            st.subheader("🔐 会员登录")
            phone_input = st.text_input("手机号码", placeholder="请输入手机号", max_chars=11)
            code_input = st.text_input("激活码 / Key", placeholder="请输入专属 Key", type="password")
            
            if st.button("立即登录", type="primary", use_container_width=True):
                try:
                    valid_accounts = st.secrets["VALID_ACCOUNTS"]
                    login_success = False
                    expire_date_str = ""
                    for account_str in valid_accounts:
                        parts = account_str.split(":")
                        if len(parts) == 3 and phone_input == parts[0].strip() and code_input == parts[1].strip():
                            exp_date = datetime.strptime(parts[2].strip(), "%Y-%m-%d")
                            if datetime.now() > exp_date:
                                st.error(f"❌ 会员已于 {parts[2]} 到期")
                                return
                            login_success = True
                            expire_date_str = parts[2]
                            break
                    
                    if login_success:
                        st.session_state.logged_in = True
                        st.session_state.user_phone = phone_input
                        st.session_state.expire_date = expire_date_str
                        # 登录时重置所有状态
                        if 'current_image' in st.session_state: del st.session_state['current_image']
                        if 'up_file' in st.session_state: del st.session_state['up_file']
                        if 'cam_file' in st.session_state: del st.session_state['cam_file']
                        
                        logger.info(f"⭐⭐⭐ [MONITOR] LOGIN SUCCESS | User: {phone_input}")
                        st.rerun()
                    else:
                        st.error("账号或激活码错误")
                except Exception as e:
                    st.error(f"配置错误: {e}")

        st.warning("💎 **获取激活码 / 续费请联系微信：BayernGomez**")
        with st.expander("📲 安装教程"):
            st.markdown("iPhone: Safari分享 -> 添加到主屏幕\nAndroid: Chrome菜单 -> 添加到主屏幕")

# ================= 4. 主程序 =================
def show_main_app():
    if not configure_random_key():
        st.stop()

    if st.session_state.dark_mode:
        st.markdown("""<style>
        .stApp {background-color: #121212; color: #E0E0E0;}
        .result-card {background-color: #1E1E1E; color: #E0E0E0;}
        section[data-testid="stSidebar"] {background-color: #1E1E1E;}
        [data-baseweb="input"] {background-color: #262626; color: white;}
        </style>""", unsafe_allow_html=True)

    with st.sidebar:
        # 侧边栏 Logo
        st.markdown(f"""
        <div style="display: flex; align-items: center; margin-bottom: 20px;">
            <img src="data:image/png;base64,{LEAF_ICON_B64}" style="width: 40px; height: 40px; margin-right: 10px;">
            <h3 style="margin:0;">用户中心</h3>
        </div>
        """, unsafe_allow_html=True)
        
        st.info(f"👤 {st.session_state.user_phone}")
        st.caption(f"有效期: {st.session_state.expire_date}")
        
        st.markdown("---")
        mode_select = st.radio("模式选择:", ["📷 日常快评", "🧐 专业艺术"], index=0)

        st.markdown("---")
        with st.expander("🕒 历史记录", expanded=False):
            if not st.session_state.history:
                st.caption("暂无记录")
            else:
                for idx, item in enumerate(reversed(st.session_state.history)):
                    with st.popover(f"📄 {item['time']} - {item['mode']}"):
                        st.markdown(item['content'])

        with st.expander("🛠️ 设置", expanded=True):
            font_size = st.slider("字体大小", 14, 24, st.session_state.font_size)
            if font_size != st.session_state.font_size:
                st.session_state.font_size = font_size
                st.rerun()
            
            new_dark = st.toggle("🌙 深色模式", value=st.session_state.dark_mode)
            if new_dark != st.session_state.dark_mode:
                st.session_state.dark_mode = new_dark
                st.rerun()
                
            show_exif_info = st.checkbox("显示参数 (EXIF)", value=True)

        if st.button("退出登录", use_container_width=True):
            st.session_state.logged_in = False
            # 退出清理
            if 'current_image' in st.session_state: del st.session_state['current_image']
            st.rerun()
            
        st.markdown("---")
        st.caption("Ver: V28.0 Final")

    st.markdown(f"<style>.stMarkdown p, .stMarkdown li {{font-size: {font_size}px !important; line-height: 1.6;}}</style>", unsafe_allow_html=True)

    if "日常" in mode_select:
        real_model = "gemini-2.0-flash-lite-preview-02-05"
        active_prompt = """你是一位亲切的摄影博主“智影”。
请严格按照 Markdown 格式输出，标题与内容之间空一行。
# 🌟 综合评分: {分数}/10

### 📝 影像笔记
> {点评}

### 🎨 手机修图参数表 (Wake/iPhone)
| 参数 | 数值 | 目的 |
| :--- | :--- | :--- |
| ... | ... | ... |

### 📸 随手拍建议
...

---
**🌿 智影寄语:** {金句}"""
        status_msg = "✨ 正在生成手机修图方案..."
        banner_text = "日常记录 | 适用：朋友圈、手机摄影、快速出片"
        banner_bg = "#e8f5e9" if not st.session_state.dark_mode else "#1b5e20"
    else:
        real_model = "gemini-2.5-flash"
        active_prompt = """你是一位视觉总监“智影”。
请严格按照 Markdown 格式输出，标题与内容之间空一行。
# 🏆 艺术总评: {分数}/10

### 👁️ 视觉深度解析
...

### 🎨 商业后期面板 (Lightroom/C1)
| 模块 | 参数 | 建议 |
| :--- | :--- | :--- |
| ... | ... | ... |

### 🎓 大师进阶课
...

---
**🌿 智影寄语:** {哲理}"""
        status_msg = "🧠 正在进行商业级光影分析..."
        banner_text = "专业创作 | 适用：单反微单、商业修图、作品集"
        banner_bg = "#e3f2fd" if not st.session_state.dark_mode else "#0d47a1"

    # 主页 Header
    st.markdown(f"""
    <div style="display: flex; align-items: center; margin-bottom: 20px;">
        <img src="data:image/png;base64,{LEAF_ICON_B64}" style="width: 50px; height: 50px; margin-right: 15px;">
        <h1 style="margin:0;">智影 | 影像私教</h1>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown(f"""
    <div style="background-color: {banner_bg}; padding: 15px; border-radius: 10px; margin-bottom: 20px; color: {'#333' if not st.session_state.dark_mode else '#eee'};">
        <small>{banner_text}</small>
    </div>
    """, unsafe_allow_html=True)

    # --- 修复核心：简单的图片流转 ---
    # 放弃复杂的 on_change，使用最原始可靠的逻辑
    
    tab1, tab2 = st.tabs(["📂 上传照片", "📷 现场拍摄"])
    
    # 只要有新输入，就更新 session_state['current_image']
    with tab1:
        f = st.file_uploader("支持 JPG/PNG", type=["jpg","png","webp"], key="up_file")
        if f: 
            st.session_state.current_image = Image.open(f).convert('RGB')
            # 如果上传了文件，清除相机的缓存，防止冲突
            if 'cam_file' in st.session_state and st.session_state.cam_file:
                st.session_state.cam_file = None
            
    with tab2:
        c = st.camera_input("点击拍摄", key="cam_file")
        if c: 
            st.session_state.current_image = Image.open(c).convert('RGB')
            # 如果拍了照，清除上传的缓存
            if 'up_file' in st.session_state and st.session_state.up_file:
                st.session_state.up_file = None

    if st.button("🗑️ 清空重置 / 换张图", use_container_width=True):
        st.session_state.current_image = None
        st.session_state.current_report = None
        # 强制清理组件缓存
        st.rerun()

    # --- 分析逻辑 ---
    if st.session_state.get('current_image'):
        st.divider()
        c1, c2 = st.columns([1, 1.2])
        
        with c1:
            st.image(st.session_state.current_image, caption="待分析影像", use_container_width=True)
            if show_exif_info:
                exif = get_exif_data(st.session_state.current_image)
                if exif:
                    with st.expander("📷 拍摄参数"): st.json(exif)
        
        with c2:
            if not st.session_state.current_report:
                user_req = st.text_input("备注 (可选):", placeholder="例如：想修出日系感...")
                
                if st.button("🚀 开始评估", type="primary", use_container_width=True):
                    with st.status(status_msg, expanded=True) as s:
                        logger.info(f"⭐⭐⭐ [MONITOR] ACTION | User: {st.session_state.user_phone} | Mode: {mode_select}")
                        
                        generation_config = genai.types.GenerationConfig(temperature=0.1)
                        model = genai.GenerativeModel(real_model, system_instruction=active_prompt)
                        
                        msg = "分析此图。"
                        if user_req: msg += f" 备注：{user_req}"
                        
                        response = model.generate_content([msg, st.session_state.current_image], generation_config=generation_config)
                        
                        st.session_state.current_report = response.text
                        st.session_state.current_req = user_req
                        s.update(label="✅ 分析完成", state="complete", expanded=False)
                        st.rerun()
            
            if st.session_state.current_report:
                st.markdown(f'<div class="result-card">{st.session_state.current_report}</div>', unsafe_allow_html=True)
                
                # 自动存历史 (去重)
                current_time = datetime.now().strftime("%H:%M")
                new_record = {"time": current_time, "mode": mode_select, "content": st.session_state.current_report}
                
                # 如果历史记录为空，或者最新一条不是当前的，就追加
                if not st.session_state.history or st.session_state.history[-1]['content'] != st.session_state.current_report:
                    st.session_state.history.append(new_record)
                    if len(st.session_state.history) > 5: st.session_state.history.pop(0)

                btn_c1, btn_c2 = st.columns(2)
                with btn_c1:
                    html_report = create_html_report(st.session_state.current_report, st.session_state.get('current_req', ''), "")
                    st.download_button("📥 下载报告", html_report, file_name="智影报告.html", mime="text/html", use_container_width=True)
                
                with btn_c2:
                    if st.button("❤️ 加入收藏", use_container_width=True):
                        st.session_state.favorites.append(new_record)
                        st.toast("已收藏！", icon="⭐")

if __name__ == "__main__":
    if st.session_state.logged_in:
        show_main_app()
    else:
        show_login_page()