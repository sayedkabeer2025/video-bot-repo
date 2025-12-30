# -*- coding: utf-8 -*-
import streamlit as st
import feedparser
import requests
from bs4 import BeautifulSoup
from moviepy.editor import AudioFileClip, VideoClip, CompositeAudioClip, afx
from PIL import Image, ImageDraw, ImageFont
import numpy as np
import os
import asyncio
import edge_tts
import json
import glob
import random
import arabic_reshaper
from bidi.algorithm import get_display

# --- 1. إعدادات الصفحة ---
st.set_page_config(page_title="PromptsLab Studio V5.2", layout="wide", page_icon="🎧")

st.markdown("""
<style>
    .stApp { background-color: #0E1117; }
    section[data-testid="stSidebar"] { background-color: #161B22; border-right: 1px solid #30363D; }
    div.stButton > button {
        background-color: #238636; color: white; border-radius: 8px; border: none;
        padding: 10px 24px; font-weight: bold; width: 100%;
    }
    div.stButton > button:hover { background-color: #2EA043; }
    h1, h2, h3, p, label, .stMarkdown, .stCaption { color: #E6EDF3 !important; font-family: 'Segoe UI', sans-serif; }
    .stSelectbox, .stSlider, .stNumberInput, .stTextArea, .stTextInput, .stRadio { color: white; }
    .stAlert { display: none; }
    .stCode { background-color: #1F2428 !important; border-radius: 5px; }
    div[data-testid="stStatusWidget"] { background-color: #161B22; border: 1px solid #30363D; color: white; }
</style>
""", unsafe_allow_html=True)

# --- المتغيرات ---
BLOG_FEED_URL = "https://promptslab.blogspot.com/feeds/posts/default"
TEMP_IMG = "temp_app_img.jpg"
TEMP_VOICE = "temp_app_voice.mp3"
TEMP_PREVIEW = "temp_preview.mp3" # ملف المعاينة
TEMP_SUBS = "temp_subs.json"
OUTPUT_FILENAME = "final_studio_video.mp4"
MUSIC_FOLDER = "music"

# --- دالة مربع النسخ ---
def render_copyable_field(label, text, height=100, help_text=""):
    st.markdown(f"**{label}**")
    if height < 50:
        edited_text = st.text_input(label, value=text, label_visibility="collapsed", help=help_text)
    else:
        edited_text = st.text_area(label, value=text, height=height, label_visibility="collapsed", help=help_text)
    
    st.caption(f"👇 انسخ {label} من الزر الصغير في الزاوية:")
    st.code(edited_text, language="markdown")
    return edited_text

# --- معالجة العربي ---
def process_text_display(text):
    try:
        reshaped_text = arabic_reshaper.reshape(text)
        bidi_text = get_display(reshaped_text)
        return bidi_text
    except:
        return text

# --- دوال المساعدة ---
def get_large_font():
    font_size = 120
    # أولاً: ابحث عن الخط المرفق مع المشروع
    if os.path.exists("font.ttf"):
        return ImageFont.truetype("font.ttf", font_size)
    
    # ثانياً: إذا لم نجد، ابحث في مسارات الويندوز (للاحتياط)
    font_paths = ["C:/Windows/Fonts/arialbd.ttf", "C:/Windows/Fonts/arial.ttf"]
    for path in font_paths:
        if os.path.exists(path):
            try: return ImageFont.truetype(path, font_size)
            except: continue
            
    # أخيراً: الخط الافتراضي
    return ImageFont.load_default()

def ensure_music_exists():
    if not os.path.exists(MUSIC_FOLDER): os.makedirs(MUSIC_FOLDER)
    default_tracks = {
        "lofi_chill.mp3": "https://cdn.pixabay.com/download/audio/2022/05/27/audio_1808fbf07a.mp3",
        "upbeat_tech.mp3": "https://cdn.pixabay.com/download/audio/2022/03/15/audio_c8c8a73467.mp3"
    }
    for name, url in default_tracks.items():
        path = os.path.join(MUSIC_FOLDER, name)
        if not os.path.exists(path):
            try:
                with open(path, 'wb') as f: f.write(requests.get(url + "?filename=" + name).content)
            except: pass

# --- دالة معاينة الصوت (الجديدة) ---
async def play_voice_preview(voice_id):
    # تحديد نص العينة بناءً على اللغة
    if "ar-" in voice_id:
        text = "مرحباً، هذا نموذج تجريبي لصوتي، أتمنى أن ينال إعجابكم."
    else:
        text = "Hello! This is a sample preview of my voice. I hope you like it."
        
    communicate = edge_tts.Communicate(text, voice_id)
    await communicate.save(TEMP_PREVIEW)

# --- المولد الذكي ---
def generate_smart_script(title, lang="Arabic"):
    title_lower = title.lower()
    if lang == "Arabic":
        default_keyword = "الذكاء الاصطناعي"
        base_script = "عايز تطلع صورة زي دي؟ {tip} في البرومبت بتاعك. النتيجة مبهرة! جربها وقولي رأيك، الكود في البايو."
        tips = {
            "lighting": ("السر كله في الإضاءة. استخدم كلمة Volumetric Lighting", "الإضاءة السينمائية"),
            "portrait": ("عشان تطلع تفاصيل البشرة دي، جرب تستخدم 8k resolution و ultra realistic", "تصوير البورتريه"),
            "face": ("عشان تطلع تفاصيل البشرة دي، جرب تستخدم 8k resolution و ultra realistic", "تصوير البورتريه"),
            "anime": ("عايز ستايل ياباني أصلي؟ استخدم Niji Style في البرومبت", "الأنمي"),
            "default": ("عايز تطلع جودة زي دي؟ السر في التفاصيل. استخدم كلمات وصف دقيقة للإضاءة والخامات", "الذكاء الاصطناعي")
        }
    else:
        default_keyword = "AI Art"
        base_script = "Want to create an image like this? {tip} in your prompt. The result is stunning! Check the link in bio for the code."
        tips = {
            "lighting": ("The secret is in the lighting. Use 'Volumetric Lighting'", "Cinematic Lighting"),
            "portrait": ("To get these skin details, try using '8k resolution' and 'ultra realistic'", "Portrait Photography"),
            "anime": ("Want an authentic Japanese style? Use 'Niji Style' parameter", "Anime Style"),
            "default": ("Want high quality like this? The secret is in the details. Use precise words for lighting and textures", "AI Generation")
        }

    selected_tip = tips["default"][0]
    selected_keyword = tips["default"][1]
    
    for key in tips:
        if key in title_lower and key != "default":
            selected_tip = tips[key][0]
            selected_keyword = tips[key][1]
            break
            
    script = base_script.format(tip=selected_tip)
    return script, selected_keyword

# --- يوتيوب ---
def generate_youtube_data(title, keyword, lang="Arabic"):
    if lang == "Arabic":
        yt_title = f"كيف تصمم {title} بالذكاء الاصطناعي 🤖✨ | {keyword}"
        yt_desc = f"""هل تبحث عن أفضل برومبت لعمل {title}؟
في هذا الفيديو القصير نستعرض نتيجة مذهلة باستخدام الذكاء الاصطناعي.

📌 البرومبت كامل موجود في الرابط في البايو.

#AIArt #Midjourney #PromptsLab #{keyword.replace(" ", "_")}"""
        tags = f"AI Art, Midjourney, {keyword}, تصميم صور, ذكاء اصطناعي, {title.replace(' ', ', ')}"
    else:
        yt_title = f"How to Create {title} with AI 🤖✨ | {keyword}"
        yt_desc = f"""Looking for the best prompt to create {title}?
In this short video, we showcase amazing AI results.

📌 Full Prompt Link in Bio.

Don't forget to subscribe for daily prompts!
#AIArt #Midjourney #PromptsLab #{keyword.replace(" ", "_")}"""
        tags = f"AI Art, Midjourney, {keyword}, image generation, AI tutorial, {title.replace(' ', ', ')}"
        
    return yt_title, yt_desc, tags

# --- دوال المعالجة ---
async def generate_tts_with_timings(text, voice, audio_file, subs_file):
    communicate = edge_tts.Communicate(text, voice)
    word_timings = []
    with open(audio_file, "wb") as file:
        async for chunk in communicate.stream():
            if chunk["type"] == "audio": file.write(chunk["data"])
            elif chunk["type"] == "WordBoundary":
                start = chunk["offset"] / 10_000_000
                end = (chunk["offset"] + chunk["duration"]) / 10_000_000
                word = chunk["text"]
                word_timings.append({"start": start, "end": end, "text": word})
    
    if not word_timings:
        try:
            temp_audio = AudioFileClip(audio_file)
            duration = temp_audio.duration
            temp_audio.close()
            words = text.split()
            if len(words) > 0:
                time_per_word = duration / len(words)
                curr = 0.0
                for word in words:
                    word_timings.append({"start": curr, "end": curr + time_per_word, "text": word})
                    curr += time_per_word
        except: pass
    
    with open(subs_file, "w", encoding="utf-8") as f:
        json.dump(word_timings, f, ensure_ascii=False)

def make_frame_generator(img_path, subs_file, sync_offset):
    original_img = Image.open(img_path).convert('RGB')
    target_w, target_h = 1080, 1920
    word_timings = []
    if os.path.exists(subs_file):
        with open(subs_file, "r", encoding="utf-8") as f: word_timings = json.load(f)

    zoom_factor = 1.2
    base_w, base_h = int(target_w * zoom_factor), int(target_h * zoom_factor)
    ratio = max(base_w / original_img.width, base_h / original_img.height)
    resized_w, resized_h = int(original_img.width * ratio), int(original_img.height * ratio)
    base_img = original_img.resize((resized_w, resized_h), Image.LANCZOS)
    font = get_large_font()
    
    def make_frame(t):
        scale = 1.0 - (0.015 * t)
        current_w, current_h = int(target_w / scale), int(target_h / scale)
        center_x, center_y = base_img.width // 2, base_img.height // 2
        left = max(0, center_x - (current_w // 2))
        top = max(0, center_y - (current_h // 2))
        frame = base_img.crop((left, top, left + current_w, top + current_h))
        frame = frame.resize((target_w, target_h), Image.BICUBIC)
        
        draw = ImageDraw.Draw(frame)
        active_word = ""
        for w in word_timings:
            adj_start = w["start"] + sync_offset
            adj_end = w["end"] + sync_offset
            if adj_start <= t <= adj_end + 0.2: active_word = w["text"]
        
        if active_word:
            display_text = process_text_display(active_word)
            try: bbox = draw.textbbox((0, 0), display_text, font=font); w_width = bbox[2] - bbox[0]
            except AttributeError: w_width, _ = draw.textsize(display_text, font=font)
            x_pos = (target_w - w_width) / 2
            y_pos = 1450
            stroke_width = 6
            for x_off in range(-stroke_width, stroke_width+1):
                for y_off in range(-stroke_width, stroke_width+1):
                    draw.text((x_pos+x_off, y_pos+y_off), display_text, font=font, fill="black")
            draw.text((x_pos, y_pos), display_text, font=font, fill="#FFD700")
        return np.array(frame.convert("RGB"))
    return make_frame

# --- 2. الواجهة ---
ensure_music_exists()

with st.sidebar:
    st.title("🎬 Studio V5.2")
    page = st.radio("القائمة:", ["صناعة الفيديو", "مكتبة الفيديوهات", "الإعدادات"], label_visibility="collapsed")
    st.divider()
    st.info("تم إضافة ميزة معاينة الصوت 🎧")

if page == "صناعة الفيديو":
    col_settings, col_preview = st.columns([1, 2]) 
    feed = feedparser.parse(BLOG_FEED_URL)

    with col_settings:
        st.subheader("1️⃣ اللغة والمحتوى")
        video_lang = st.radio("اللغة:", ["Arabic", "English"], horizontal=True)
        
        if feed.entries:
            post_options = {entry.title: entry for entry in feed.entries[:10]}
            selected_title = st.selectbox("اختر المقال:", list(post_options.keys()))
            selected_entry = post_options[selected_title]
            clean_title = selected_entry.title.replace("|", " ").replace("-", " ").strip()
            
            content_val = selected_entry.content[0].value if 'content' in selected_entry else selected_entry.summary
            soup = BeautifulSoup(content_val, 'html.parser')
            img_tag = soup.find('img')
            img_url = img_tag['src'] if img_tag else None
            
            if img_url: st.image(img_url, caption="الصورة المختارة", use_container_width=True)
            
            st.divider()
            st.subheader("2️⃣ السكربت والنسخ")
            auto_script, auto_keyword = generate_smart_script(clean_title, lang=video_lang)
            final_script = render_copyable_field("📝 نص الفيديو (السكربت)", auto_script, height=130)
            
            st.divider()
            with st.expander("📺 بيانات يوتيوب (Copy-Ready)", expanded=True):
                yt_title, yt_desc, yt_tags = generate_youtube_data(clean_title, auto_keyword, lang=video_lang)
                render_copyable_field("📌 عنوان الفيديو", yt_title, height=0)
                render_copyable_field("📄 الوصف", yt_desc, height=150)
                render_copyable_field("🏷️ الكلمات المفتاحية", yt_tags, height=80)

            st.divider()
            st.subheader("3️⃣ الأصوات الكاملة")
            
            # قائمة الأصوات
            if video_lang == "Arabic":
                voice_options = [
                    ("سلمى (مصر - أنثى)", "ar-EG-SalmaNeural"),
                    ("شاكر (مصر - ذكر)", "ar-EG-ShakirNeural"),
                    ("حامد (السعودية - ذكر)", "ar-SA-HamedNeural"),
                    ("زارية (السعودية - أنثى)", "ar-SA-ZariyahNeural"),
                    ("فاطمة (الإمارات - أنثى)", "ar-AE-FatimaNeural"),
                    ("حمدان (الإمارات - ذكر)", "ar-AE-HamdanNeural"),
                    ("تيم (الأردن - ذكر)", "ar-JO-TaimNeural"),
                    ("ريم (تونس - أنثى)", "ar-TN-ReemNeural"),
                ]
            else:
                voice_options = [
                    ("Christopher (US - Male)", "en-US-ChristopherNeural"),
                    ("Aria (US - Female)", "en-US-AriaNeural"),
                    ("Guy (US - Male)", "en-US-GuyNeural"),
                    ("Jenny (US - Female)", "en-US-JennyNeural"),
                    ("Eric (US - Male)", "en-US-EricNeural"),
                    ("Michelle (US - Female)", "en-US-MichelleNeural"),
                    ("Ryan (UK - Male)", "en-GB-RyanNeural"),
                    ("Sonia (UK - Female)", "en-GB-SoniaNeural"),
                    ("Libby (UK - Female)", "en-GB-LibbyNeural"),
                ]
            
            # --- تنسيق زر المعاينة بجانب القائمة ---
            col_v1, col_v2 = st.columns([3, 1])
            with col_v1:
                voice_choice = st.selectbox("المعلق:", voice_options, format_func=lambda x: x[0])
                voice_id = voice_choice[1]
            with col_v2:
                st.write("") # مسافة لضبط المحاذاة
                st.write("")
                if st.button("🔊 سماع", help="اضغط لسماع عينة من هذا الصوت"):
                    asyncio.run(play_voice_preview(voice_id))
                    st.audio(TEMP_PREVIEW)
            
            music_files = [f for f in os.listdir(MUSIC_FOLDER) if f.endswith(".mp3")]
            music_choice = st.selectbox("الموسيقى:", ["بدون موسيقى"] + music_files)
            music_vol = st.slider("الصوت:", 0.0, 0.5, 0.1)
            sync_offset = st.number_input("تزامن النص (Offset):", -2.0, 2.0, 0.0, 0.1)

        else: st.error("لا توجد مقالات.")

    with col_preview:
        st.subheader("4️⃣ التصدير")
        preview_placeholder = st.empty()
        preview_placeholder.markdown("""<div style="background-color:black; height:400px; border-radius:10px; display:flex; align-items:center; justify-content:center; color:gray; border: 1px dashed #333;"><h3>شاشة العرض</h3></div>""", unsafe_allow_html=True)
        
        st.write("")
        if st.button("✨ إنشاء الفيديو (Generate)", use_container_width=True):
            if img_url:
                with st.status("🚀 جاري العمل...", expanded=True) as status:
                    try:
                        st.write("📥 تحميل...")
                        with open(TEMP_IMG, 'wb') as f: f.write(requests.get(img_url).content)
                        
                        st.write("🎙️ توليد الصوت...")
                        asyncio.run(generate_tts_with_timings(final_script, voice_id, TEMP_VOICE, TEMP_SUBS))
                        
                        st.write("🎬 دمج الفيديو...")
                        audio = AudioFileClip(TEMP_VOICE)
                        dur = audio.duration + 1.0
                        clip = VideoClip(make_frame_generator(TEMP_IMG, TEMP_SUBS, sync_offset), duration=dur)
                        
                        final_audio = audio
                        if music_choice != "بدون موسيقى":
                            m_path = os.path.join(MUSIC_FOLDER, music_choice)
                            bg = afx.audio_loop(AudioFileClip(m_path), duration=dur).volumex(music_vol)
                            final_audio = CompositeAudioClip([audio, bg])
                        
                        safe_title = "".join([c for c in clean_title if c.isalnum() or c in (' ', '-', '_')]).strip()[:20]
                        final_filename = f"Video_{safe_title}.mp4"
                        
                        clip.set_audio(final_audio).write_videofile(final_filename, fps=24, codec='libx264', audio_codec='aac', preset='ultrafast', logger=None)
                        
                        status.update(label="✅ تم!", state="complete", expanded=False)
                        preview_placeholder.video(final_filename)
                        
                        with open(final_filename, "rb") as file:
                            st.download_button("⬇️ تحميل MP4", data=file, file_name=final_filename, mime="video/mp4", use_container_width=True)
                            
                    except Exception as e:
                        status.update(label="❌ خطأ", state="error")
                        st.error(f"تفاصيل الخطأ: {e}")

elif page == "مكتبة الفيديوهات":
    st.header("📂 الأرشيف")
    video_files = glob.glob("*.mp4")
    if not video_files: st.info("فارغ.")
    else:
        cols = st.columns(3)
        for i, vid in enumerate(video_files):
            with cols[i % 3]:
                st.video(vid)
                st.caption(vid)
                with open(vid, "rb") as f:
                    st.download_button(f"تحميل", f, file_name=vid, key=f"dl_{i}")

elif page == "الإعدادات":
    st.header("⚙️ الضبط")
    st.write("V5.2 - Preview Edition")