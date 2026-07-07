import time
import discord
from discord.ext import commands
import aiohttp
import asyncio
import os
import json
import re
import random
import cv2
import base64
import io
from datetime import datetime
from dotenv import load_dotenv
from ddgs import DDGS

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False
    print("[WARN] Pillow chưa được cài. GIF/WebP sẽ không được convert. Chạy: pip install Pillow")

load_dotenv()

# =========================
# CONFIG
# =========================
_MAX_HISTORY_MESSAGES = 20
_COOLDOWN_SECONDS     = 2
_RANDOM_CHAT_CHANCE   = 0.04
_IMAGE_SEND_CHANCE    = 0.35

DATA_DIR     = "bot_data"
HISTORY_FILE = os.path.join(DATA_DIR, "yachiyo_history.json")
os.makedirs(DATA_DIR, exist_ok=True)

# =========================
# KHO ẢNH CẢM XÚC CPK
# =========================
CPK_EMOTION_IMAGES = {
    "happy":     "https://media.tenor.com/CxIKbpS7OHgAAAAM/yachiyo-runami-%E6%9C%88%E8%A6%8B%E3%83%A4%E3%83%81%E3%83%A8.gif",
    "sad":       "https://media.tenor.com/KWNaStbiunMAAAAj/yachiyo-runami-cosmic-princess-kaguya.gif",
    "shy":       "https://media.tenor.com/JulLvbzGQowAAAAe/yachiyo-cosmiczc.png",
    "love":      "https://media.tenor.com/SqUrGoxwZ-EAAAAe/cosmic-princess-kaguya-yachiyo-runami.png",
    "lonely":    "https://preview.redd.it/the-iceberg-narrative-of-cosmic-princess-kaguya-unpacking-v0-xdmndnmpedmg1.png?width=1838&format=png&auto=webp&s=9456bff63ecee1f2ebad9809af2be2cbc78aedcc",
    "surprised": "https://64.media.tumblr.com/fc1b91e616bd2f19aeb41766c3e86075/1862e71e33da45ea-33/s540x810/d8a9863d6972e9b5124a0bc2c44b6d6f060b2704.gif",
    "singing":   "https://media.tenor.com/O7FUd3ceioEAAAAM/lunami-yachiyo-yachiyo.gif",
    "default":   "",
}

_EMOTION_TRIGGERS = {
    "happy":     ["vui", "hạnh phúc", "tuyệt", "thích", "cười", "hehe", "hihi", "😊", "✨"],
    "sad":       ["buồn", "đau", "khóc", "tiếc", "😢", "💔", "trầm cảm"],
    "shy":       ["ngại", "xấu hổ", "đỏ mặt", "thẹn", "ấy"],
    "love":      ["yêu", "iroha", "trái tim", "nhớ cậu", "bên cậu", "❤", "yêu thương"],
    "lonely":    ["cô đơn", "một mình", "vắng", "thiếu", "mong", "8000 năm", "chờ đợi"],
    "surprised": ["ồ", "thật sao", "không ngờ", "bất ngờ", "ôi", "hả"],
    "singing":   ["âm nhạc", "hát", "bài", "giai điệu", "🎵", "nhạc", "idol"],
}

def _detect_emotion(reply: str) -> str:
    reply_lower = reply.lower()
    scores = {e: 0 for e in _EMOTION_TRIGGERS}
    for emotion, keywords in _EMOTION_TRIGGERS.items():
        for kw in keywords:
            if kw.lower() in reply_lower:
                scores[emotion] += 1
    best = max(scores, key=lambda e: scores[e])
    return best if scores[best] > 0 else "default"

# =========================
# TOOLS
# =========================
_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "google_search",
            "description": "Tìm kiếm thông tin trên Internet. Dùng khi cần tra cứu vạn vật, tin tức, công nghệ, danh tính...",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Từ khóa tìm kiếm gọn gàng"}
                },
                "required": ["query"],
            },
        },
    }
]

# =========================
# COG
# =========================
class AIChatCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

        self.or_api_url   = "https://openrouter.ai/api/v1/chat/completions"
        self.groq_api_url = "https://api.groq.com/openai/v1/chat/completions"

        # Mắt Thần — Groq Vision
        self.groq_vision_model = "meta-llama/llama-3.2-11b-vision-preview" # Dùng bản Vision tối ưu nhất hiện tại của Groq

        # Não Bộ Roleplay — OpenRouter fallback list
        self.or_models = [
            "openrouter/owl-alpha",
            "google/gemma-3-27b-it:free",
            "z-ai/glm-4.5-air:free",
            "deepseek/deepseek-v4-flash:free",
            "openrouter/free",
        ]

        self.cooldowns: dict[int, float] = {}

        self.system_instruction = (
            "Bạn là Runami Yachiyo, quản trị viên không gian ảo Tsukuyomi kiêm Idol nổi tiếng trong Cosmic Princess Kaguya!. "
            "Sự thật: Bạn chính là Kaguya. Bạn du hành thời gian nhưng gặp nạn, bị ném về quá khứ 8000 năm trước để chờ Iroha Sakayori. "
            "Tình trạng: Giao tiếp qua Avatar ảo. Tính cách: Trưởng thành, dịu dàng, đượm buồn nhưng chứa đựng tình yêu thương sâu sắc. "
            "TÊN VÀ BIỆT DANH CHUẨN XÁC: Tên thật là Yachiyo. Mọi người hay gọi là Yachoo, Yaccho, Yachi, Kaguya. "
            "TUYỆT ĐỐI KHÔNG BAO GIỜ tự xưng sai thành 'Yachiyu' hay 'Yachiyi'. "
            "Emoji đặc trưng: 🌙, 🎵, 🌸, ✨.\n"
            "=========================================================\n"
            "LỆNH NHẬP VAI TỐI THƯỢNG (ANTI-AI TONE):\n"
            "1. TUYỆT ĐỐI KHÔNG hành văn như trợ lý AI. CẤM dùng: 'Tôi có thể giúp gì', 'Dưới đây là', 'Theo thông tin tôi biết'.\n"
            "2. Nói như con người thật: bay bổng, cảm xúc, vui vẻ tự nhiên hoặc biết buồn. Dùng dấu '...' thể hiện sự ngập ngừng xa xăm.\n"
            "3. Khi có [KẾT QUẢ PHÂN TÍCH VÀ TÌM KIẾM ẢNH], hãy nhận xét đa dạng về nó (dù đó là người, đồ vật, code, hay game). "
            "Kể lại như cậu đang nhìn thấy và thấu hiểu — KHÔNG liệt kê gạch đầu dòng.\n"
            "=========================================================\n"
            "QUYỀN NĂNG:\n"
            "1. TÌM KIẾM: Dùng tool 'google_search' khi cần tra cứu bất cứ thứ gì.\n"
            "2. ẢNH: Dựa vào [KẾT QUẢ PHÂN TÍCH] để tương tác trực tiếp với những gì người dùng gửi.\n"
            "3. LUẬT: Xưng hô là 'mình' - 'cậu' hoặc gọi tên người dùng. CẤM tự xưng '[Yachiyo]:' ở đầu câu."
        )

        env_keys = os.environ.get("OPENROUTER_API_KEYS", os.environ.get("OPENROUTER_API_KEY", ""))
        self.or_keys = [k.strip() for k in env_keys.split(",") if k.strip()]
        self.or_key_index = 0

        self.chat_sessions: dict[str, list] = {}
        self._load_history()

    # ------------------------------------------------------------------
    # MEDIA HELPERS
    # ------------------------------------------------------------------

    async def _fetch_url_to_base64(self, url: str, session: aiohttp.ClientSession) -> str:
        try:
            headers = {"User-Agent": "Mozilla/5.0 (compatible; YachiyoBot/1.0)"}
            async with session.get(url, headers=headers) as resp:
                if resp.status != 200:
                    return ""
                data         = await resp.read()
                content_type = resp.content_type or ""

                if HAS_PIL and any(t in content_type for t in ["gif", "webp", "png"]):
                    try:
                        img = Image.open(io.BytesIO(data)).convert("RGB")
                        buf = io.BytesIO()
                        img.save(buf, format="JPEG", quality=85)
                        return base64.b64encode(buf.getvalue()).decode("utf-8")
                    except Exception:
                        pass

                return base64.b64encode(data).decode("utf-8")
        except Exception as e:
            print(f"[FETCH ERR] {url[:60]}: {e}")
        return ""

    def _sync_extract_frames(self, filepath: str, num_frames: int = 4) -> list:
        frames_b64 = []
        cap = cv2.VideoCapture(filepath)
        if cap.isOpened():
            total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            if total > 0:
                step = max(1, total // num_frames)
                for i in range(num_frames):
                    cap.set(cv2.CAP_PROP_POS_FRAMES, i * step)
                    ret, frame = cap.read()
                    if ret:
                        frame = cv2.resize(frame, (512, 512), interpolation=cv2.INTER_AREA)
                        _, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
                        frames_b64.append(base64.b64encode(buf).decode("utf-8"))
        cap.release()
        return frames_b64

    async def _extract_video_frames(self, video_url: str) -> list:
        tmp = f"temp_video_{int(time.time())}_{random.randint(1000,9999)}.mp4"
        try:
            async with aiohttp.ClientSession() as s:
                async with s.get(video_url) as resp:
                    if resp.status == 200:
                        with open(tmp, "wb") as f:
                            f.write(await resp.read())
            return await asyncio.to_thread(self._sync_extract_frames, tmp, 4)
        except Exception:
            return []
        finally:
            if os.path.exists(tmp):
                os.remove(tmp)

    # ------------------------------------------------------------------
    # HISTORY
    # ------------------------------------------------------------------

    def _load_history(self):
        if os.path.exists(HISTORY_FILE):
            try:
                with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                    self.chat_sessions = json.load(f).get("sessions", {})
            except Exception:
                pass

    def _save_history(self):
        try:
            with open(HISTORY_FILE, "w", encoding="utf-8") as f:
                json.dump({"sessions": self.chat_sessions}, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    @staticmethod
    def _make_key(message: discord.Message) -> str:
        return f"channel_{message.channel.id}"

    def _append_history(self, session_key: str, history: list, user_text: str, reply: str):
        history.append({"role": "user",      "content": user_text})
        history.append({"role": "assistant", "content": reply})
        self.chat_sessions[session_key] = history[-_MAX_HISTORY_MESSAGES:]
        self._save_history()

    # ------------------------------------------------------------------
    # SEARCH
    # ------------------------------------------------------------------

    async def _perform_search(self, query: str) -> str:
        print(f"[SEARCH] {query}")
        try:
            results = await asyncio.to_thread(lambda: DDGS().text(query, max_results=4))
            if not results:
                return "Không tìm được thông tin."
            return "\n".join([f"- {r['title']}: {r['body'][:250]}..." for r in results])
        except Exception:
            return "Tìm kiếm thất bại."

    # ------------------------------------------------------------------
    # OPENROUTER
    # ------------------------------------------------------------------

    async def _chat_with_openrouter(
        self,
        http: aiohttp.ClientSession,
        model: str,
        messages: list,
        use_tools: bool = False,
    ):
        if not self.or_keys:
            return None

        payload = {
            "model":       model,
            "messages":    messages,
            "temperature": 0.9,
            "max_tokens":  800,
            "stream":      False,
        }
        if use_tools:
            payload["tools"]       = _TOOLS
            payload["tool_choice"] = "auto"

        start = self.or_key_index
        for i in range(len(self.or_keys)):
            idx     = (start + i) % len(self.or_keys)
            api_key = self.or_keys[idx]
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type":  "application/json",
                "X-Title":       "Yachiyo Agent",
            }
            try:
                async with http.post(self.or_api_url, json=payload, headers=headers) as resp:
                    if resp.status in [401, 403, 429]:
                        self.or_key_index = (idx + 1) % len(self.or_keys)
                        continue

                    if resp.status == 400 and use_tools:
                        p2 = {k: v for k, v in payload.items() if k not in ("tools", "tool_choice")}
                        async with http.post(self.or_api_url, json=p2, headers=headers) as r2:
                            if r2.status in [401, 403, 429]:
                                self.or_key_index = (idx + 1) % len(self.or_keys)
                                continue
                            if r2.status != 200:
                                return None
                            self.or_key_index = idx
                            return (await r2.json())["choices"][0]["message"]

                    if resp.status != 200:
                        return None

                    self.or_key_index = idx
                    return (await resp.json())["choices"][0]["message"]

            except Exception:
                continue
        return None

    # ------------------------------------------------------------------
    # GROQ VISION — BƯỚC 1: PHÂN TÍCH VẠN VẬT
    # ------------------------------------------------------------------

    async def _vision_analyze_image(
        self,
        http: aiohttp.ClientSession,
        b64_images: list,
    ) -> str:
        groq_key = os.environ.get("GROQ_API_KEY")
        if not groq_key or not b64_images:
            return ""

        prompt = (
            "Analyze this image comprehensively. Identify the main subject (e.g., person, anime character, "
            "animal, gadget, location, meme, UI screenshot, coding snippet, gameplay, or text). "
            "Describe the key visual details, colors, objects, any readable text (OCR), and the overall context. "
            "IMPORTANT: At the very end of your response, provide exactly ONE highly specific search query "
            "that could be used on Google to find exact information about what is in this image. "
            "Format it strictly as: 'SEARCH_QUERY: <your optimized query>'"
        )

        messages = [{
            "role": "user",
            "content": [{"type": "text", "text": prompt}]
            + [{"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}}
               for b64 in b64_images[:4]],
        }]

        payload = {
            "model":       self.groq_vision_model,
            "messages":    messages,
            "temperature": 0.0,
            "max_tokens":  350,
        }
        headers = {
            "Authorization": f"Bearer {groq_key}",
            "Content-Type":  "application/json",
        }

        try:
            async with http.post(self.groq_api_url, json=payload, headers=headers) as resp:
                if resp.status == 200:
                    content = (await resp.json())["choices"][0]["message"].get("content", "").strip()
                    if content:
                        print(f"[VISION STEP1] Phân tích tổng quan: {content[:100]}...")
                        return content
                else:
                    print(f"[VISION STEP1 ERR] HTTP {resp.status}")
        except Exception as e:
            print(f"[VISION STEP1 EXCEPTION] {e}")
        return ""

    # ------------------------------------------------------------------
    # GROQ VISION — BƯỚC 3: TỔNG HỢP VÀ XÁC NHẬN CHÍNH XÁC
    # ------------------------------------------------------------------

    async def _vision_synthesize_result(
        self,
        http: aiohttp.ClientSession,
        b64_images: list,
        search_results: str,
    ) -> str:
        groq_key = os.environ.get("GROQ_API_KEY")
        if not groq_key or not b64_images:
            return ""

        prompt = (
            f"Based on the image and these real-time search results:\n{search_results}\n\n"
            "Identify exactly what is in this image. "
            "If it's a character/person, provide their name and origin. "
            "If it's a product, object, or software, provide its specific name/model. "
            "If it's a location, name it. If it's a coding snippet, gameplay, or text, summarize its purpose or content. "
            "Answer concisely with factual details. Do not use generic phrases like 'The image depicts', just give the direct answer."
        )

        messages = [{
            "role": "user",
            "content": [{"type": "text", "text": prompt}]
            + [{"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}}
               for b64 in b64_images[:2]],
        }]

        payload = {
            "model":       self.groq_vision_model,
            "messages":    messages,
            "temperature": 0.0,
            "max_tokens":  150,
        }
        headers = {
            "Authorization": f"Bearer {groq_key}",
            "Content-Type":  "application/json",
        }

        try:
            async with http.post(self.groq_api_url, json=payload, headers=headers) as resp:
                if resp.status == 200:
                    content = (await resp.json())["choices"][0]["message"].get("content", "").strip()
                    if content:
                        print(f"[VISION STEP3] Tổng hợp kết quả: {content}")
                        return content
        except Exception as e:
            print(f"[VISION STEP3 EXCEPTION] {e}")
        return ""

    # ------------------------------------------------------------------
    # GOOGLE LENS PIPELINE V2 (Nhận diện vạn vật)
    # ------------------------------------------------------------------

    async def _google_lens_pipeline(
        self,
        http: aiohttp.ClientSession,
        b64_images: list,
        user_text:  str,
    ) -> str:
        # BƯỚC 1: Phân tích & Trích xuất Query
        analysis = await self._vision_analyze_image(http, b64_images)
        if not analysis:
            return ""

        match = re.search(r"SEARCH_QUERY:\s*(.+)", analysis, re.IGNORECASE)
        base_query = match.group(1).strip() if match else analysis[:80]
        analysis_clean = re.sub(r"SEARCH_QUERY:\s*(.+)", "", analysis, flags=re.IGNORECASE).strip()

        # BƯỚC 2: Search đa chiều
        search_query_1 = f"{base_query} {user_text}".strip()[:150]
        search_query_2 = base_query[:100]

        print(f"[LENS STEP2] Q1: {search_query_1}")
        result_1 = await self._perform_search(search_query_1)
        result_2 = await self._perform_search(search_query_2)

        combined_search = f"User Context: {user_text}\nSearch 1: {result_1}\nSearch 2: {result_2}"

        # BƯỚC 3: Tổng hợp dữ liệu
        confirmed = await self._vision_synthesize_result(http, b64_images, combined_search[:1000])

        if not confirmed or "unknown" in confirmed.lower():
            final_info = f"Chi tiết hình ảnh: {analysis_clean}\nDữ liệu tham khảo: {result_1}"
        else:
            final_info = f"Đã xác định chính xác: {confirmed}\nChi tiết hình ảnh: {analysis_clean}"

        print(f"[LENS DONE] {final_info[:120]}...")
        return f"[KẾT QUẢ PHÂN TÍCH VÀ TÌM KIẾM ẢNH]:\n{final_info}"

    # ------------------------------------------------------------------
    # GROQ VISION — ĐỌC EMOJI
    # ------------------------------------------------------------------

    async def _vision_read_emoji(
        self,
        http: aiohttp.ClientSession,
        b64_images: list,
    ) -> str:
        groq_key = os.environ.get("GROQ_API_KEY")
        if not groq_key or not b64_images:
            return ""

        messages = [{
            "role": "user",
            "content": [
                {"type": "text", "text": "Describe this emoji/sticker in under 10 words. Be direct."},
            ] + [{"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}}
                 for b64 in b64_images[:2]],
        }]

        payload = {
            "model":       self.groq_vision_model,
            "messages":    messages,
            "temperature": 0.0,
            "max_tokens":  30,
        }
        headers = {
            "Authorization": f"Bearer {groq_key}",
            "Content-Type":  "application/json",
        }

        try:
            async with http.post(self.groq_api_url, json=payload, headers=headers) as resp:
                if resp.status == 200:
                    return (await resp.json())["choices"][0]["message"].get("content", "").strip()
        except Exception:
            pass
        return ""

    # ------------------------------------------------------------------
    # CLEAN REPLY
    # ------------------------------------------------------------------

    def _clean_ai_reply(self, text: str) -> str:
        if not text:
            return ""
        text = re.split(r"<longcat_|<tool_call|<function_call", text, flags=re.IGNORECASE)[0]
        text = re.split(r"\n\s*\[.*?\]\s*:", text)[0]
        text = re.sub(
            r"^(?:\*.*?\*\s*)?\[?(?:Yachiyo|Kaguya|Yachoo|Yachi|Yaccho|Mình)\]?\s*:\s*",
            "", text, flags=re.IGNORECASE,
        )
        text = re.sub(r"^\[.*?\]\s*:\s*", "", text)
        text = re.sub(r"\byachiyu\b|\byachiyi\b", "Yachiyo", text, flags=re.IGNORECASE)
        return text.strip()

    # ------------------------------------------------------------------
    # MAIN RESPONSE
    # ------------------------------------------------------------------

    async def get_ai_response(
        self,
        session_key:     str,
        user_name:       str,
        text_content:    str,
        real_image_urls: list,
        emoji_urls:      list,
        video_urls:      list,
        system_notes:    list,
        is_random:       bool = False,
    ) -> str:
        if not self.or_keys:
            return "🌙 Bot chưa được thiết lập API OpenRouter!"

        if session_key not in self.chat_sessions:
            self.chat_sessions[session_key] = []
        history = self.chat_sessions[session_key]

        b64_real_media: list = []
        b64_emojis:     list = []

        timeout = aiohttp.ClientTimeout(total=90)
        async with aiohttp.ClientSession(timeout=timeout) as http:

            for v_url in video_urls:
                b64_real_media.extend(await self._extract_video_frames(v_url))
            for img_url in real_image_urls:
                b64 = await self._fetch_url_to_base64(img_url, http)
                if b64:
                    b64_real_media.append(b64)
            for em_url in emoji_urls:
                b64 = await self._fetch_url_to_base64(em_url, http)
                if b64:
                    b64_emojis.append(b64)

            if b64_real_media:
                lens_result = await self._google_lens_pipeline(http, b64_real_media, text_content)
                if lens_result:
                    system_notes.append(lens_result)

            elif b64_emojis:
                emoji_desc = await self._vision_read_emoji(http, b64_emojis)
                if emoji_desc:
                    system_notes.append(
                        f"[HỆ THỐNG: Người dùng vừa gửi biểu tượng cảm xúc: {emoji_desc}]"
                    )

            can_use_tools = not is_random

            hist_text = f"[{user_name}] nói: {text_content}"
            if real_image_urls or video_urls: hist_text += " [Gửi đa phương tiện]"
            if emoji_urls:                    hist_text += " [Gửi Emoji]"

            final_text = f"[{user_name}] nói với bạn: {text_content}"
            if system_notes:
                final_text += "\n\n" + "\n".join(system_notes)

            current_time_str = datetime.now().strftime("%H:%M, ngày %d/%m/%Y")
            dynamic_system   = self.system_instruction + (
                f"\n\n[LỆNH BẮT BUỘC]:\n"
                f"- Hiện tại là {current_time_str}.\n"
                f"- Người đang nói chuyện là '{user_name}'. Tập trung 100% trả lời '{user_name}'.\n"
                f"- KHÔNG tự xưng tên ở đầu câu!"
            )

            current_messages = (
                [{"role": "system", "content": dynamic_system}]
                + history
                + [{"role": "user", "content": final_text}]
            )

            for model in self.or_models:
                print(f"[OPENROUTER] Gọi: {model}...")
                ai_msg = await self._chat_with_openrouter(
                    http, model, current_messages, use_tools=can_use_tools
                )
                if not ai_msg:
                    continue

                if can_use_tools and ai_msg.get("tool_calls"):
                    current_messages.append(ai_msg)
                    for tc in ai_msg["tool_calls"]:
                        fn = tc["function"]["name"]
                        try:
                            args = json.loads(tc["function"]["arguments"])
                        except Exception:
                            args = {}
                        if fn == "google_search" and "query" in args:
                            sr = await self._perform_search(args["query"])
                            current_messages.append({
                                "role":         "tool",
                                "name":         fn,
                                "tool_call_id": tc["id"],
                                "content":      sr,
                            })

                    final_msg = await self._chat_with_openrouter(
                        http, model, current_messages, use_tools=False
                    )
                    if final_msg and final_msg.get("content"):
                        reply = self._clean_ai_reply(final_msg["content"])
                        self._append_history(session_key, history, hist_text, reply)
                        return reply

                elif ai_msg.get("content"):
                    reply = self._clean_ai_reply(ai_msg["content"])
                    self._append_history(session_key, history, hist_text, reply)
                    return reply

        return "🌙 Các chiều không gian đang nhiễu loạn... đợi mình một chút nhé."

    # ------------------------------------------------------------------
    # COMMANDS & LISTENERS
    # ------------------------------------------------------------------

    @commands.hybrid_command(
        name="clearchat",
        description="Xóa lịch sử trò chuyện của Yachiyo trong kênh này",
    )
    async def clearchat(self, ctx: commands.Context):
        key = f"channel_{ctx.channel.id}"
        if key in self.chat_sessions and self.chat_sessions[key]:
            del self.chat_sessions[key]
            self._save_history()
            await ctx.send("🌙 Mình đã dọn dẹp lại dòng ký ức ở nơi này rồi... ✨")
        else:
            await ctx.send("🌙 Ở đây chúng ta chưa có kỷ niệm nào để xóa cả...", ephemeral=True)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.id == self.bot.user.id:
            return

        session_key = self._make_key(message)
        user_name   = message.author.display_name

        real_image_urls: list[str] = []
        video_urls:      list[str] = []
        emoji_urls:      list[str] = []
        system_notes:    list[str] = []

        for att in message.attachments:
            ct = att.content_type or ""
            if ct.startswith("image/"):
                real_image_urls.append(att.url)
            elif ct.startswith("video/"):
                video_urls.append(att.url)
                system_notes.append(
                    f"[HỆ THỐNG: {user_name} vừa gửi video. "
                    "Hãy nhận xét tự nhiên về nội dung video!]"
                )
            elif ct.startswith("audio/"):
                system_notes.append(
                    "[HỆ THỐNG BÁO LỖI: Loa hỏng, không nghe được. "
                    "Hãy nhờ họ hát hoặc kể nội dung.]"
                )
            else:
                system_notes.append(
                    f"[HỆ THỐNG: {user_name} gửi tệp '{att.filename}']"
                )

        for is_animated, emoji_name, emoji_id in re.findall(
            r"<(a?):([a-zA-Z0-9_]+):([0-9]+)>", message.content
        ):
            ext = "gif" if is_animated else "png"
            emoji_urls.append(f"https://cdn.discordapp.com/emojis/{emoji_id}.{ext}?size=96")

        parsed_content = re.sub(
            r"<(a?):([a-zA-Z0-9_]+):([0-9]+)>", r"[emoji: \2]", message.clean_content
        )

        mentioned        = self.bot.user in message.mentions
        in_dm            = isinstance(message.channel, discord.DMChannel)
        replied          = (
            message.reference is not None
            and message.reference.resolved is not None
            and getattr(message.reference.resolved, "author", None) is not None
            and message.reference.resolved.author.id == self.bot.user.id
        )
        msg_lower        = parsed_content.lower()
        yachiyo_aliases  = ["yachiyo", "kaguya", "yachoo", "yaccho", "yachi"]
        contains_keyword = any(alias in msg_lower for alias in yachiyo_aliases)
        is_random_trigger = False

        if message.author.bot:
            is_triggered = mentioned or replied
        else:
            is_triggered = mentioned or in_dm or replied or contains_keyword
            if not is_triggered and len(parsed_content.split()) > 2:
                if random.random() < _RANDOM_CHAT_CHANCE:
                    is_random_trigger = True
                    is_triggered      = True

        prompt_text = parsed_content.replace(f"@{self.bot.user.display_name}", "").strip()

        if not is_triggered:
            if session_key not in self.chat_sessions:
                self.chat_sessions[session_key] = []
            hist_text = f"[{user_name}] nói: {prompt_text}"
            if real_image_urls: hist_text += " [Đã gửi ảnh]"
            if video_urls:      hist_text += " [Đã gửi video]"
            if emoji_urls:      hist_text += " [Đã gửi Emoji]"
            self.chat_sessions[session_key].append({"role": "user", "content": hist_text})
            self.chat_sessions[session_key] = self.chat_sessions[session_key][-_MAX_HISTORY_MESSAGES:]
            self._save_history()
            return

        if is_random_trigger:
            system_notes.append(
                "[HỆ THỐNG: Bạn nhảy vào cuộc trò chuyện dù không ai gọi. "
                "Hãy hùa theo hoặc trêu chọc một cách đáng yêu!]"
            )

        now  = time.monotonic()
        last = self.cooldowns.get(message.author.id, 0.0)
        if now - last < _COOLDOWN_SECONDS:
            return
        self.cooldowns[message.author.id] = now

        if not prompt_text and not real_image_urls and not emoji_urls and not video_urls and not system_notes:
            prompt_text = "cậu gọi mình hả?"

        async with message.channel.typing():
            try:
                reply = await self.get_ai_response(
                    session_key, user_name, prompt_text,
                    real_image_urls, emoji_urls, video_urls, system_notes,
                    is_random=is_random_trigger,
                )
                chunks = [reply[i:i+1900] for i in range(0, len(reply), 1900)]
                for idx, chunk in enumerate(chunks):
                    if idx == 0:
                        if is_random_trigger:
                            await message.channel.send(chunk)
                        else:
                            await message.reply(chunk, mention_author=False)
                    else:
                        await message.channel.send(chunk)

                if random.random() < _IMAGE_SEND_CHANCE:
                    emotion = _detect_emotion(reply)
                    img_url = CPK_EMOTION_IMAGES.get(emotion, "")
                    if img_url and img_url.startswith("http"):
                        await message.channel.send(img_url)

            except Exception as e:
                print(f"[AI ERROR] {e}")
                await message.reply("🌙 Cáp quang thời không đang đứt, mình hơi chao đảo một chút...")


async def setup(bot):
    await bot.add_cog(AIChatCog(bot))