"""
TikTok Account & Video Analytics GUI
====================================
Aplikasi desktop berbasis Tkinter untuk:
1. Mengecek frekuensi unggah akun TikTok dilengkapi grafik interaktif yang modern.
2. Menganalisis rata-rata view 10 video terakhir akun TikTok beserta metrik performa lainnya.

Dibuat dengan Python, Tkinter, Matplotlib, curl_cffi, dan yt-dlp.
"""

import sys
import os
import re
import json
import threading
import datetime
import webbrowser
from typing import List, Dict, Any, Optional

import tkinter as tk
from tkinter import ttk, messagebox, filedialog

import matplotlib
matplotlib.use("TkAgg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
import matplotlib.dates as mdates
import matplotlib.ticker as ticker

# Optional network dependencies
try:
    from curl_cffi import requests as cffi_requests
    CURL_CFFI_AVAILABLE = True
except ImportError:
    CURL_CFFI_AVAILABLE = False
    import requests as cffi_requests

try:
    import yt_dlp
    from yt_dlp.networking.impersonate import ImpersonateTarget
    YT_DLP_AVAILABLE = True
except ImportError:
    YT_DLP_AVAILABLE = False

from bs4 import BeautifulSoup


# ==========================================
# PALET WARNA MODERN (DARK THEME)
# ==========================================
COLORS = {
    "bg_dark": "#121217",
    "card_bg": "#1c1c24",
    "card_alt": "#242430",
    "card_border": "#2c2c3c",
    "text_primary": "#FFFFFF",
    "text_secondary": "#9CA3AF",
    "text_muted": "#6B7280",
    "accent_pink": "#FE2C55",      # TikTok Pink/Red
    "accent_cyan": "#25F4EE",      # TikTok Cyan
    "accent_purple": "#8B5CF6",
    "accent_yellow": "#FBBF24",
    "accent_green": "#10B981",
    "button_hover": "#E0264A",
    "table_alt": "#1f1f2b",
    "table_sel": "#312E81"
}


def format_number(val: Optional[float or int]) -> str:
    """Format angka menjadi ringkas (contoh: 1.2M, 450K, 120)."""
    if val is None:
        return "-"
    try:
        num = float(val)
    except (ValueError, TypeError):
        return str(val)

    if num >= 1_000_000_000:
        return f"{num / 1_000_000_000:.1f}B"
    elif num >= 1_000_000:
        return f"{num / 1_000_000:.1f}M"
    elif num >= 1_000:
        return f"{num / 1_000:.1f}K"
    else:
        return f"{int(num):,}"


def format_full_number(val: Optional[float or int]) -> str:
    """Format angka dengan pemisah koma ribuan."""
    if val is None:
        return "-"
    try:
        return f"{int(val):,}"
    except (ValueError, TypeError):
        return str(val)


def format_duration(seconds: Optional[float or int]) -> str:
    """Format durasi video ke bentuk menit:detik atau detik (contoh: 01:15 atau 45s)."""
    if seconds is None:
        return "-"
    try:
        s = int(round(float(seconds)))
        if s <= 0:
            return "-"
        m, sec = divmod(s, 60)
        h, m = divmod(m, 60)
        if h > 0:
            return f"{h}:{m:02d}:{sec:02d}"
        elif m > 0:
            return f"{m:02d}:{sec:02d} ({s}s)"
        else:
            return f"{sec}s"
    except (ValueError, TypeError):
        return f"{seconds}s"


# ==========================================
# SCRAPING & ANALYTICS ENGINE
# ==========================================
class TikTokEngine:
    """Mesin pengambil dan penganalisis data TikTok."""

    @staticmethod
    def get_sec_uid(username: str) -> Optional[Dict[str, Any]]:
        """Mengambil secUid dan profil dasar dari username."""
        username = username.strip().lstrip("@")
        if not username:
            return None

        url = f"https://www.tiktok.com/@{username}"
        headers = {
            "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Mobile/15E148 Safari/604.1",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7",
        }

        for attempt in range(3):
            try:
                if CURL_CFFI_AVAILABLE:
                    r = cffi_requests.get(url, headers=headers, impersonate="chrome", timeout=12)
                else:
                    r = cffi_requests.get(url, headers=headers, timeout=12)

                if r.status_code == 200:
                    soup = BeautifulSoup(r.text, "html.parser")
                    s = soup.find("script", id="__UNIVERSAL_DATA_FOR_REHYDRATION__")
                    sec_uid = None
                    profile_info = {
                        "username": username,
                        "nickname": username,
                        "secUid": None,
                        "avatar": "",
                        "signature": "",
                        "followerCount": 0,
                        "followingCount": 0,
                        "heartCount": 0,
                        "videoCount": 0
                    }

                    if s and s.string:
                        try:
                            data = json.loads(s.string)
                            user_detail = data.get("__DEFAULT_SCOPE__", {}).get("webapp.user-detail", {})
                            user_info = user_detail.get("userInfo", {})
                            user_obj = user_info.get("user", {})
                            stats_obj = user_info.get("stats", {})

                            sec_uid = user_obj.get("secUid")
                            if sec_uid:
                                profile_info.update({
                                    "username": user_obj.get("uniqueId", username),
                                    "nickname": user_obj.get("nickname", username),
                                    "secUid": sec_uid,
                                    "avatar": user_obj.get("avatarLarger", ""),
                                    "signature": user_obj.get("signature", ""),
                                    "followerCount": stats_obj.get("followerCount", 0),
                                    "followingCount": stats_obj.get("followingCount", 0),
                                    "heartCount": stats_obj.get("heartCount", 0),
                                    "videoCount": stats_obj.get("videoCount", 0)
                                })
                                return profile_info
                        except Exception:
                            pass

                    # Fallback Regex jika JSON parsing beda struktur
                    match = re.search(r'"secUid":"([^"]+)"', r.text)
                    if match:
                        profile_info["secUid"] = match.group(1)
                        nick_match = re.search(r'"nickname":"([^"]+)"', r.text)
                        if nick_match:
                            profile_info["nickname"] = nick_match.group(1)
                        return profile_info
            except Exception as e:
                pass
        return None

    @staticmethod
    def fetch_videos(sec_uid: str, count: int = 15) -> List[Dict[str, Any]]:
        """Mengambil metadata video terbaru dengan yt-dlp flat extraction."""
        if not YT_DLP_AVAILABLE:
            raise RuntimeError("Library yt-dlp belum terinstall!")

        url = f"tiktokuser:{sec_uid}"
        ydl_opts = {
            "extract_flat": True,
            "playlist_items": f"1-{count}",
            "quiet": True,
            "no_warnings": True,
        }

        # Menggunakan impersonate chrome jika curl_cffi aktif
        try:
            ydl_opts["impersonate"] = ImpersonateTarget.from_str("chrome")
        except Exception:
            pass

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            res = ydl.extract_info(url, download=False)
            entries = res.get("entries", [])

        videos = []
        for e in entries:
            if not e:
                continue
            ts = e.get("timestamp")
            dt = datetime.datetime.fromtimestamp(ts) if ts else None
            vid = {
                "id": e.get("id"),
                "title": e.get("title") or e.get("description") or "Tanpa Judul",
                "timestamp": ts,
                "datetime": dt,
                "view_count": e.get("view_count", 0) or 0,
                "like_count": e.get("like_count", 0) or 0,
                "comment_count": e.get("comment_count", 0) or 0,
                "repost_count": e.get("repost_count", 0) or 0,
                "duration": e.get("duration", 0) or 0,
                "url": e.get("url") or f"https://www.tiktok.com/@tiktok/video/{e.get('id')}"
            }
            videos.append(vid)

        return videos

    @staticmethod
    def get_demo_data(username: str = "creator.indonesia", count: int = 15) -> (Dict[str, Any], List[Dict[str, Any]]):
        """Menyediakan data demo realistis untuk pengujian instan / offline sesuai jumlah count."""
        now = datetime.datetime.now()
        demo_profile = {
            "username": username,
            "nickname": f"Kreator Populer ({username})",
            "secUid": "DEMO_SEC_UID_123456",
            "avatar": "",
            "signature": "Konten Kreator Edukasi & Entertainment | Upload Rutin Setiap Minggu",
            "followerCount": 1_250_000,
            "followingCount": 180,
            "heartCount": 24_500_000,
            "videoCount": 245
        }

        sample_titles_pool = [
            "5 Tips rahasia bikin konten cepat FYP tahun ini! 🚀",
            "Behind the scene shooting project terbaru kemarin seru banget",
            "POV: Ketika kamu lupa save draft video sebelum close app 😂",
            "Tutorial transisi editing video cuma pakai HP! Coba sekarang",
            "Q&A bareng viewers: Dari mana ide konten setiap hari?",
            "Unboxing & review kamera baru untuk ngonten harian",
            "Jangan lakukan 3 kesalahan fatal ini saat upload video!",
            "Eksperimen algoritma: Jam upload terbaik menurut data analitik",
            "Day in my life sebagai content creator freelance di Jakarta",
            "Review jujur gear lighting murah vs mahal, worth it mana?",
            "Tips konsisten upload video tanpa burnout!",
            "Terima kasih 1 Juta Followers! Giveaway spesial buat kalian 🎉",
            "Mitos vs Fakta seputar shadowban TikTok yang wajib kamu tahu",
            "Cara riset sound yang lagi trending sebelum orang lain pakai",
            "Bongkar rahasia hook 3 detik pertama yang bikin penonton betah",
            "Setup studio mini di kamar dengan budget hemat tapi estetik",
            "Alasan kenapa views kamu tiba-tiba stuck di 200 views",
            "Kolaborasi bareng kreator favorit! Jangan lupa tonton sampai habis",
            "Rutinitas pagi sebelum mulai scripting dan produksi konten",
            "Review aplikasi editing video terbaik untuk pemula di 2026",
            "Storytime: Pengalaman pertama kali di-endorse brand besar",
            "Tips meningkatkan rasio likes dan komentar secara alami",
            "Inspirasi ide konten buat kamu yang lagi kena creative block",
            "Cara membaca TikTok Analytics untuk menaikkan performa akun",
            "Live streaming tips: Cara dapetin interaksi tinggi dari viewers",
            "Evolusi kontenku dari awal bikin akun sampai sekarang!",
            "Eksperimen upload 3 video sehari selama seminggu penuh",
            "Cara bikin thumbnail TikTok yang menarik dan rapi di feed",
            "Menjawab pertanyaan tersering di kolom komentar video lalu",
            "Spill gear andalan buat mobile videography outdoor"
        ]

        import random
        random.seed(42)  # Seed agar konsisten namun variatif

        videos = []
        cur_time = now

        for i in range(count):
            title = sample_titles_pool[i % len(sample_titles_pool)]
            delta_days = random.choice([1.0, 1.5, 2.0, 2.5, 3.0, 4.0])
            cur_time = cur_time - datetime.timedelta(days=delta_days, hours=random.randint(1, 8))
            
            # Variasi views dengan beberapa video viral
            base_views = random.choice([250_000, 420_000, 680_000, 890_000, 1_150_000, 1_600_000, 2_400_000])
            views = int(base_views * random.uniform(0.85, 1.25))
            likes = int(views * random.uniform(0.08, 0.16))
            comments = int(likes * random.uniform(0.02, 0.05))

            videos.append({
                "id": f"730000000000000{i:02d}",
                "title": title,
                "timestamp": int(cur_time.timestamp()),
                "datetime": cur_time,
                "view_count": views,
                "like_count": likes,
                "comment_count": comments,
                "repost_count": int(likes * 0.03),
                "duration": random.choice([15, 30, 45, 60, 90]),
                "url": f"https://www.tiktok.com/@{username}/video/730000000000000{i:02d}"
            })

        return demo_profile, videos

    @staticmethod
    def analyze_data(videos: List[Dict[str, Any]], sample_count: int = 10) -> Dict[str, Any]:
        """Menghitung metrik views sesuai jumlah video yang diatur user dan frekuensi unggah."""
        if not videos:
            return {}

        # Ambil sejumlah video sesuai sample_count yang dipilih user
        actual_count = min(len(videos), sample_count) if sample_count > 0 else len(videos)
        analyzed_videos = videos[:actual_count]

        views = [v["view_count"] for v in analyzed_videos]
        avg_views = sum(views) / len(views) if views else 0
        total_views = sum(views)
        max_view = max(views) if views else 0
        min_view = min(views) if views else 0

        likes = [v["like_count"] for v in analyzed_videos]
        avg_likes = sum(likes) / len(likes) if likes else 0

        comments = [v["comment_count"] for v in analyzed_videos]
        avg_comments = sum(comments) / len(comments) if comments else 0
        avg_comments_10 = avg_comments

        # Analisis Durasi Video
        durations = [v.get("duration", 0) for v in analyzed_videos if v.get("duration", 0) > 0]
        avg_duration = sum(durations) / len(durations) if durations else 0
        max_duration = max(durations) if durations else 0
        min_duration = min(durations) if durations else 0

        # Analisis Jam Posting (Waktu Indonesia / Sesi Waktu)
        hours = [v["datetime"].hour for v in analyzed_videos if v.get("datetime")]
        hour_sessions = {
            "Pagi (05-11)": 0,
            "Siang (11-15)": 0,
            "Sore (15-18)": 0,
            "Malam (18-24)": 0,
            "Dini Hari (00-05)": 0
        }
        hour_counts_24 = {h: 0 for h in range(24)}
        for h in hours:
            hour_counts_24[h] += 1
            if 5 <= h < 11:
                hour_sessions["Pagi (05-11)"] += 1
            elif 11 <= h < 15:
                hour_sessions["Siang (11-15)"] += 1
            elif 15 <= h < 18:
                hour_sessions["Sore (15-18)"] += 1
            elif 18 <= h < 24:
                hour_sessions["Malam (18-24)"] += 1
            else:
                hour_sessions["Dini Hari (00-05)"] += 1

        most_active_session = max(hour_sessions.items(), key=lambda x: x[1])[0] if hours else "-"
        most_common_hour = max(hour_counts_24.items(), key=lambda x: x[1])[0] if hours else None

        # Analisis Frekuensi Unggah
        # Urutkan secara kronologis (tertua ke terbaru)
        valid_dates = [v["datetime"] for v in videos if v.get("datetime")]
        valid_dates_sorted = sorted(valid_dates)

        intervals_days = []
        for i in range(1, len(valid_dates_sorted)):
            diff = (valid_dates_sorted[i] - valid_dates_sorted[i-1]).total_seconds() / 86400.0
            intervals_days.append(diff)

        avg_interval_days = sum(intervals_days) / len(intervals_days) if intervals_days else 0

        # Frekuensi deskriptif
        if avg_interval_days <= 0:
            freq_text = "Data belum cukup"
        elif avg_interval_days < 1.0:
            freq_text = f"~{24.0 * avg_interval_days:.1f} jam sekali (>1 video/hari)"
        elif avg_interval_days <= 1.5:
            freq_text = f"Hampir setiap hari (~{avg_interval_days:.1f} hari/video)"
        elif avg_interval_days <= 7.0:
            videos_per_week = 7.0 / avg_interval_days
            freq_text = f"~{videos_per_week:.1f} video / minggu (tiap {avg_interval_days:.1f} hari)"
        else:
            freq_text = f"Jarang (~tiap {avg_interval_days:.1f} hari)"

        # Distribusi Hari dalam Seminggu
        days_name = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"]
        day_counts = {day: 0 for day in days_name}
        for dt in valid_dates:
            day_counts[days_name[dt.weekday()]] += 1

        most_active_day = max(day_counts.items(), key=lambda x: x[1])[0] if valid_dates else "-"

        return {
            "sample_count": actual_count,
            "analyzed_videos": analyzed_videos,
            "views": views,
            "avg_views": avg_views,
            "total_views": total_views,
            "max_view": max_view,
            "min_view": min_view,
            "avg_likes": avg_likes,
            "avg_comments": avg_comments,
            "avg_duration": avg_duration,
            "max_duration": max_duration,
            "min_duration": min_duration,
            "hour_sessions": hour_sessions,
            "hour_counts_24": hour_counts_24,
            "most_active_session": most_active_session,
            "most_common_hour": most_common_hour,
            # Backward compatibility aliases
            "last_10": analyzed_videos,
            "views_10": views,
            "avg_views_10": avg_views,
            "total_views_10": total_views,
            "max_view_10": max_view,
            "min_view_10": min_view,
            "avg_likes_10": avg_likes,
            "avg_comments_10": avg_comments,
            "avg_interval_days": avg_interval_days,
            "freq_text": freq_text,
            "intervals_days": intervals_days,
            "day_counts": day_counts,
            "most_active_day": most_active_day,
            "valid_dates_sorted": valid_dates_sorted
        }


# ==========================================
# TKINTER GUI APPLICATION
# ==========================================
class TikTokAnalyticsApp(tk.Tk):
    """Antarmuka GUI Desktop TikTok Analytics."""

    def __init__(self):
        super().__init__()
        self.title("TikTok Analytics - Frekuensi Unggah & Rata-rata View")
        self.geometry("1180x820")
        self.minsize(980, 700)
        self.configure(bg=COLORS["bg_dark"])

        self.current_profile: Optional[Dict[str, Any]] = None
        self.current_videos: List[Dict[str, Any]] = []
        self.current_analytics: Dict[str, Any] = {}

        self.setup_styles()
        self.create_layout()

        # Otomatis isi dengan contoh akun terkenal
        self.entry_username.insert(0, "mrbeast")

    def setup_styles(self):
        """Konfigurasi gaya ttk untuk tema gelap modern."""
        self.style = ttk.Style(self)
        self.style.theme_use("clam")

        # Global Font & Backgrounds
        self.style.configure(".", background=COLORS["bg_dark"], foreground=COLORS["text_primary"], font=("Segoe UI", 10))

        # Notebook (Tabs)
        self.style.configure("TNotebook", background=COLORS["bg_dark"], borderwidth=0)
        self.style.configure("TNotebook.Tab", background=COLORS["card_bg"], foreground=COLORS["text_secondary"],
                             padding=[18, 9], font=("Segoe UI", 10, "bold"), borderwidth=0)
        self.style.map("TNotebook.Tab",
                       background=[("selected", COLORS["card_alt"]), ("active", COLORS["card_border"])],
                       foreground=[("selected", COLORS["accent_cyan"]), ("active", COLORS["text_primary"])])

        # Treeview (Table)
        self.style.configure("Treeview",
                             background=COLORS["card_bg"],
                             foreground=COLORS["text_primary"],
                             fieldbackground=COLORS["card_bg"],
                             rowheight=32,
                             font=("Segoe UI", 9),
                             borderwidth=0)
        self.style.map("Treeview",
                       background=[("selected", COLORS["table_sel"])],
                       foreground=[("selected", COLORS["text_primary"])])

        self.style.configure("Treeview.Heading",
                             background=COLORS["card_alt"],
                             foreground=COLORS["text_primary"],
                             font=("Segoe UI", 10, "bold"),
                             padding=[10, 8],
                             borderwidth=0)
        self.style.map("Treeview.Heading", background=[("active", COLORS["card_border"])])

        # Progressbar
        self.style.configure("Accent.Horizontal.TProgressbar",
                             troughcolor=COLORS["card_bg"],
                             background=COLORS["accent_pink"],
                             thickness=6)

    def create_layout(self):
        """Membangun tata letak aplikasi GUI."""
        # Top Header Bar
        header_frame = tk.Frame(self, bg=COLORS["card_bg"], height=70)
        header_frame.pack(fill=tk.X, side=tk.TOP)
        header_frame.pack_propagate(False)

        title_container = tk.Frame(header_frame, bg=COLORS["card_bg"])
        title_container.pack(side=tk.LEFT, padx=25, pady=12)

        lbl_logo = tk.Label(title_container, text="🎵 TikTok", font=("Segoe UI", 16, "bold"),
                            fg=COLORS["accent_pink"], bg=COLORS["card_bg"])
        lbl_logo.pack(side=tk.LEFT)

        lbl_title = tk.Label(title_container, text=" Analytics Studio", font=("Segoe UI", 16, "bold"),
                             fg=COLORS["text_primary"], bg=COLORS["card_bg"])
        lbl_title.pack(side=tk.LEFT)

        lbl_sub = tk.Label(title_container, text=" | Frekuensi Unggah & Analisis Rata-Rata Views Video",
                           font=("Segoe UI", 10), fg=COLORS["text_secondary"], bg=COLORS["card_bg"])
        lbl_sub.pack(side=tk.LEFT, padx=6, pady=(3, 0))

        # Input & Control Card Frame
        control_card = tk.Frame(self, bg=COLORS["card_bg"], bd=1, relief=tk.FLAT, highlightthickness=1,
                                highlightbackground=COLORS["card_border"])
        control_card.pack(fill=tk.X, padx=20, pady=(15, 10))

        control_inner = tk.Frame(control_card, bg=COLORS["card_bg"])
        control_inner.pack(fill=tk.X, padx=20, pady=14)

        lbl_input = tk.Label(control_inner, text="Username Akun TikTok:", font=("Segoe UI", 10, "bold"),
                             fg=COLORS["text_primary"], bg=COLORS["card_bg"])
        lbl_input.grid(row=0, column=0, sticky="w", padx=(0, 10))

        # Username Input
        entry_container = tk.Frame(control_inner, bg="#2C2C3A", bd=0, padx=2, pady=2)
        entry_container.grid(row=0, column=1, sticky="w", padx=(0, 15))

        lbl_at = tk.Label(entry_container, text="@", font=("Segoe UI", 11, "bold"),
                          fg=COLORS["accent_cyan"], bg="#2C2C3A")
        lbl_at.pack(side=tk.LEFT, padx=(8, 2))

        self.entry_username = tk.Entry(entry_container, font=("Segoe UI", 11), bg="#2C2C3A",
                                       fg=COLORS["text_primary"], insertbackground=COLORS["text_primary"],
                                       bd=0, width=22)
        self.entry_username.pack(side=tk.LEFT, padx=(0, 10), pady=6)
        self.entry_username.bind("<Return>", lambda e: self.start_analysis())

        # Dropdown Jumlah Video
        lbl_count = tk.Label(control_inner, text="Jumlah Video:", font=("Segoe UI", 10),
                             fg=COLORS["text_secondary"], bg=COLORS["card_bg"])
        lbl_count.grid(row=0, column=2, sticky="w", padx=(0, 8))

        self.combo_count = ttk.Combobox(control_inner, values=["5 Video", "10 Video", "15 Video", "20 Video", "30 Video", "50 Video"],
                                        state="readonly", width=11, font=("Segoe UI", 10))
        self.combo_count.current(1)  # Default 10 video
        self.combo_count.grid(row=0, column=3, sticky="w", padx=(0, 20))
        self.combo_count.bind("<<ComboboxSelected>>", self.on_count_changed)

        # Action Buttons
        self.btn_analyze = tk.Button(control_inner, text="🔍 Analisis Akun", font=("Segoe UI", 10, "bold"),
                                     bg=COLORS["accent_pink"], fg="white", activebackground=COLORS["button_hover"],
                                     activeforeground="white", bd=0, padx=18, pady=7, cursor="hand2",
                                     command=self.start_analysis)
        self.btn_analyze.grid(row=0, column=4, padx=(0, 10))

        self.btn_demo = tk.Button(control_inner, text="✨ Coba Data Demo", font=("Segoe UI", 10),
                                  bg=COLORS["card_alt"], fg=COLORS["accent_cyan"],
                                  activebackground=COLORS["card_border"], activeforeground=COLORS["accent_cyan"],
                                  bd=1, highlightthickness=1, highlightbackground=COLORS["card_border"],
                                  padx=14, pady=6, cursor="hand2", command=self.load_demo)
        self.btn_demo.grid(row=0, column=5, padx=(0, 10))

        # Status & Progress Frame
        self.status_frame = tk.Frame(control_card, bg=COLORS["card_bg"])
        self.status_frame.pack(fill=tk.X, padx=20, pady=(0, 12))

        self.lbl_status = tk.Label(self.status_frame, text="Siap menganalisis. Masukkan username dan klik 'Analisis Akun'.",
                                   font=("Segoe UI", 9), fg=COLORS["text_secondary"], bg=COLORS["card_bg"])
        self.lbl_status.pack(side=tk.LEFT)

        self.progress_bar = ttk.Progressbar(self.status_frame, style="Accent.Horizontal.TProgressbar",
                                            mode="indeterminate", length=220)

        # Profile & Stat Cards Frame
        self.stats_container = tk.Frame(self, bg=COLORS["bg_dark"])
        self.stats_container.pack(fill=tk.X, padx=20, pady=(0, 10))

        self.create_stat_cards(self.stats_container)

        # Main Notebook (Tabs)
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 15))

        # Tab 1: Grafik Rata-rata Views 10 Video Terakhir
        self.tab_views = tk.Frame(self.notebook, bg=COLORS["bg_dark"])
        self.notebook.add(self.tab_views, text="  📈 Grafik Views (10 Video Terakhir)  ")

        # Tab 2: Grafik Frekuensi Unggah
        self.tab_freq = tk.Frame(self.notebook, bg=COLORS["bg_dark"])
        self.notebook.add(self.tab_freq, text="  📅 Grafik Frekuensi Unggah  ")

        # Tab 3: Tabel Detail Video
        self.tab_table = tk.Frame(self.notebook, bg=COLORS["bg_dark"])
        self.notebook.add(self.tab_table, text="  📋 Tabel 10 Video Terakhir  ")

        # Tab 4: Insight & Ringkasan
        self.tab_insight = tk.Frame(self.notebook, bg=COLORS["bg_dark"])
        self.notebook.add(self.tab_insight, text="  💡 Ringkasan Analitik  ")

        self.create_table_tab()
        self.create_insight_tab()

        # Canvas placeholders for charts
        self.canvas_views = None
        self.canvas_freq = None

    def create_stat_cards(self, parent):
        """Membangun 4 kartu metrik utama di bagian atas."""
        parent.columnconfigure(0, weight=1)
        parent.columnconfigure(1, weight=1)
        parent.columnconfigure(2, weight=1)
        parent.columnconfigure(3, weight=1)

        def make_card(col, title, default_val, default_sub, color_border, val_color):
            card = tk.Frame(parent, bg=COLORS["card_bg"], highlightthickness=1,
                            highlightbackground=color_border, padx=14, pady=12)
            card.grid(row=0, column=col, sticky="nsew", padx=5)

            lbl_t = tk.Label(card, text=title, font=("Segoe UI", 9, "bold"),
                             fg=COLORS["text_secondary"], bg=COLORS["card_bg"])
            lbl_t.pack(anchor="w")

            lbl_v = tk.Label(card, text=default_val, font=("Segoe UI", 18, "bold"),
                             fg=val_color, bg=COLORS["card_bg"])
            lbl_v.pack(anchor="w", pady=(3, 1))

            lbl_s = tk.Label(card, text=default_sub, font=("Segoe UI", 8),
                             fg=COLORS["text_muted"], bg=COLORS["card_bg"])
            lbl_s.pack(anchor="w")
            return lbl_t, lbl_v, lbl_s

        # Card 1: Rata-Rata View (Highlight Utama)
        self.title_avg_view, self.val_avg_view, self.sub_avg_view = make_card(
            0, "⭐ RATA-RATA VIEW", "-", "Rata-rata unggahan terbaru",
            COLORS["accent_pink"], COLORS["accent_pink"]
        )

        # Card 2: Frekuensi Unggah
        self.title_freq, self.val_freq, self.sub_freq = make_card(
            1, "📅 FREKUENSI UNGGAH", "-", "Interval rata-rata antar video",
            COLORS["accent_cyan"], COLORS["accent_cyan"]
        )

        # Card 3: Video Tertinggi (Peak View)
        self.title_peak, self.val_peak, self.sub_peak = make_card(
            2, "🏆 VIEW TERTINGGI", "-", "Video terpopuler",
            COLORS["accent_yellow"], COLORS["accent_yellow"]
        )

        # Card 4: Total Followers & Likes
        self.title_profile_stat, self.val_profile_stat, self.sub_profile_stat = make_card(
            3, "👥 PROFIL KREATOR", "-", "Data pengikut & total suka akun",
            COLORS["accent_purple"], COLORS["accent_purple"]
        )

    def create_table_tab(self):
        """Membangun tabel daftar video terakhir dengan Treeview."""
        frame = tk.Frame(self.tab_table, bg=COLORS["bg_dark"])
        frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Tool bar di atas tabel
        tb_frame = tk.Frame(frame, bg=COLORS["bg_dark"])
        tb_frame.pack(fill=tk.X, pady=(0, 8))

        lbl_info = tk.Label(tb_frame, text="Klik ganda pada baris untuk membuka video di browser TikTok.",
                            font=("Segoe UI", 9, "italic"), fg=COLORS["text_secondary"], bg=COLORS["bg_dark"])
        lbl_info.pack(side=tk.LEFT)

        btn_export = tk.Button(tb_frame, text="💾 Export ke CSV", font=("Segoe UI", 9, "bold"),
                               bg=COLORS["card_alt"], fg=COLORS["text_primary"],
                               activebackground=COLORS["card_border"], bd=1, highlightthickness=1,
                               highlightbackground=COLORS["card_border"], padx=10, pady=3,
                               cursor="hand2", command=self.export_csv)
        btn_export.pack(side=tk.RIGHT)

        # Container tabel & scrollbar
        table_container = tk.Frame(frame, bg=COLORS["card_bg"])
        table_container.pack(fill=tk.BOTH, expand=True)

        columns = ("no", "date", "time", "duration", "title", "views", "likes", "comments", "link")
        self.tree = ttk.Treeview(table_container, columns=columns, show="headings", selectmode="browse")

        self.tree.heading("no", text="#")
        self.tree.heading("date", text="📅 Tanggal")
        self.tree.heading("time", text="⏰ Jam Posting")
        self.tree.heading("duration", text="⏱️ Durasi Video")
        self.tree.heading("title", text="📝 Judul / Caption")
        self.tree.heading("views", text="👁️ Views")
        self.tree.heading("likes", text="❤️ Likes")
        self.tree.heading("comments", text="💬 Komentar")
        self.tree.heading("link", text="🔗 Link URL")

        self.tree.column("no", width=36, anchor="center")
        self.tree.column("date", width=95, anchor="center")
        self.tree.column("time", width=110, anchor="center")
        self.tree.column("duration", width=105, anchor="center")
        self.tree.column("title", width=300, anchor="w")
        self.tree.column("views", width=105, anchor="e")
        self.tree.column("likes", width=90, anchor="e")
        self.tree.column("comments", width=80, anchor="e")
        self.tree.column("link", width=140, anchor="w")

        scrollbar_y = ttk.Scrollbar(table_container, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscroll=scrollbar_y.set)

        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar_y.pack(side=tk.RIGHT, fill=tk.Y)

        self.tree.bind("<Double-1>", self.on_table_double_click)

    def create_insight_tab(self):
        """Membangun tab teks ringkasan analisis & rekomendasi."""
        frame = tk.Frame(self.tab_insight, bg=COLORS["card_bg"], padx=25, pady=25,
                         highlightthickness=1, highlightbackground=COLORS["card_border"])
        frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        lbl_header = tk.Label(frame, text="Analisis Performa Akun & Pola Unggahan",
                              font=("Segoe UI", 14, "bold"), fg=COLORS["text_primary"], bg=COLORS["card_bg"])
        lbl_header.pack(anchor="w", pady=(0, 15))

        self.txt_insight = tk.Text(frame, bg=COLORS["card_bg"], fg=COLORS["text_primary"],
                                   font=("Consolas", 10), wrap=tk.WORD, bd=0, relief=tk.FLAT,
                                   highlightthickness=0, height=20)
        self.txt_insight.pack(fill=tk.BOTH, expand=True)
        self.txt_insight.insert(tk.END, "Belum ada analisis. Silakan masukkan username dan jalankan 'Analisis Akun'.")
        self.txt_insight.config(state=tk.DISABLED)

    def on_table_double_click(self, event):
        """Buka link video di web browser ketika baris tabel diklik ganda."""
        selected_item = self.tree.selection()
        if not selected_item:
            return
        item_vals = self.tree.item(selected_item[0], "values")
        if item_vals and len(item_vals) >= 9:
            url = item_vals[8]
            if url and url.startswith("http"):
                webbrowser.open(url)

    def export_csv(self):
        """Menyimpan data video yang dianalisis ke format file CSV."""
        analyzed = self.current_analytics.get("analyzed_videos") or self.current_videos
        if not analyzed:
            messagebox.showwarning("Peringatan", "Belum ada data video untuk diekspor!")
            return

        file_path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            title="Simpan Data Video TikTok"
        )
        if not file_path:
            return

        try:
            import csv
            with open(file_path, mode="w", newline="", encoding="utf-8-sig") as f:
                writer = csv.writer(f)
                writer.writerow(["No", "Video ID", "Tanggal Unggah", "Jam Posting", "Durasi (Format)", "Durasi (Detik)", "Judul", "Views", "Likes", "Comments", "URL"])
                for i, v in enumerate(analyzed, start=1):
                    dt = v.get("datetime")
                    date_str = dt.strftime("%Y-%m-%d") if dt else "-"
                    time_str = dt.strftime("%H:%M:%S") if dt else "-"
                    dur = v.get("duration", 0)
                    writer.writerow([
                        i,
                        v.get("id", "-"),
                        date_str,
                        time_str,
                        format_duration(dur),
                        dur,
                        v.get("title", "-"),
                        v.get("view_count", 0),
                        v.get("like_count", 0),
                        v.get("comment_count", 0),
                        v.get("url", "-")
                    ])
            messagebox.showinfo("Sukses", f"Data ({len(analyzed)} video) berhasil diekspor ke:\n{file_path}")
        except Exception as e:
            messagebox.showerror("Error", f"Gagal mengekspor data: {e}")

    # ==========================================
    # WORKER & LOGIC PENGAMBILAN DATA
    # ==========================================
    def set_loading(self, is_loading: bool, status_msg: str = ""):
        """Mengatur status loading pada tombol dan progress bar."""
        if is_loading:
            self.btn_analyze.config(state=tk.DISABLED)
            self.btn_demo.config(state=tk.DISABLED)
            self.progress_bar.pack(side=tk.RIGHT, padx=(0, 10))
            self.progress_bar.start(10)
        else:
            self.btn_analyze.config(state=tk.NORMAL)
            self.btn_demo.config(state=tk.NORMAL)
            self.progress_bar.stop()
            self.progress_bar.pack_forget()

        if status_msg:
            self.lbl_status.config(text=status_msg)

    def on_count_changed(self, event=None):
        """Handler ketika dropdown jumlah video diubah user."""
        if not self.current_videos or not self.current_profile:
            return
        count_str = self.combo_count.get()
        count = int(count_str.split()[0]) if count_str else 10
        
        # Jika video yang tersedia di memory sudah cukup, langsung hitung ulang & render instan
        if len(self.current_videos) >= count:
            analytics = TikTokEngine.analyze_data(self.current_videos, sample_count=count)
            self._apply_results(self.current_profile, self.current_videos, analytics)
        else:
            # Jika butuh lebih banyak video daripada yang sudah terambil, fetch ulang
            self.start_analysis()

    def start_analysis(self):
        """Memulai proses analisis dalam background thread."""
        username = self.entry_username.get().strip().lstrip("@")
        if not username:
            messagebox.showwarning("Peringatan", "Harap masukkan username TikTok terlebih dahulu!")
            return

        count_str = self.combo_count.get()
        count = int(count_str.split()[0]) if count_str else 10

        self.set_loading(True, f"Mencari profil @{username} di server TikTok...")

        threading.Thread(target=self._worker_fetch, args=(username, count), daemon=True).start()

    def _worker_fetch(self, username: str, count: int):
        """Fungsi worker yang berjalan di background thread."""
        try:
            self.update_status_safe(f"Mengambil profil dan secUid @{username}...")
            profile = TikTokEngine.get_sec_uid(username)

            if not profile or not profile.get("secUid"):
                self.after(0, lambda: self._handle_fetch_error(
                    username,
                    f"Tidak dapat menemukan secUid untuk akun '@{username}'. "
                    f"Akun mungkin privat, username salah, atau dibatasi oleh verifikasi TikTok."
                ))
                return

            sec_uid = profile["secUid"]
            fetch_count = max(count, 15)
            self.update_status_safe(f"Profil ditemukan: {profile.get('nickname', username)}. Mengambil {fetch_count} video...")

            videos = TikTokEngine.fetch_videos(sec_uid, count=fetch_count)
            if not videos:
                self.after(0, lambda: self._handle_fetch_error(
                    username,
                    f"Berhasil menemukan profil @{username}, namun tidak ada video publik yang dapat diakses."
                ))
                return

            analytics = TikTokEngine.analyze_data(videos, sample_count=count)

            # Update UI di main thread
            self.after(0, lambda: self._apply_results(profile, videos, analytics))

        except Exception as e:
            self.after(0, lambda: self._handle_fetch_error(username, str(e)))

    def update_status_safe(self, text: str):
        """Thread-safe status update."""
        self.after(0, lambda: self.lbl_status.config(text=text))

    def _handle_fetch_error(self, username: str, err_msg: str):
        """Menangani kegagalan scraping dengan opsi mencoba data demo."""
        self.set_loading(False, f"Gagal mengambil data untuk @{username}.")
        res = messagebox.askyesno(
            "Gagal Mengambil Data Live",
            f"Terjadi kendala saat mengambil data online:\n\n{err_msg}\n\n"
            f"Apakah Anda ingin memuat Data Demo (Simulasi) untuk melihat grafik dan fitur lengkapnya sekarang?"
        )
        if res:
            self.load_demo()

    def load_demo(self):
        """Memuat data demo simulasi instan sesuai jumlah video yang dipilih."""
        username = self.entry_username.get().strip().lstrip("@") or "kreator.populer"
        count_str = self.combo_count.get()
        count = int(count_str.split()[0]) if count_str else 10
        self.set_loading(True, f"Menyiapkan data simulasi demo ({count} video)...")

        def _do_demo():
            profile, videos = TikTokEngine.get_demo_data(username, count=count)
            analytics = TikTokEngine.analyze_data(videos, sample_count=count)
            self.after(200, lambda: self._apply_results(profile, videos, analytics, is_demo=True))

        threading.Thread(target=_do_demo, daemon=True).start()

    def _apply_results(self, profile: Dict[str, Any], videos: List[Dict[str, Any]], analytics: Dict[str, Any], is_demo: bool = False):
        """Menerapkan data hasil analisis ke seluruh komponen GUI."""
        self.current_profile = profile
        self.current_videos = videos
        self.current_analytics = analytics

        sample_count = analytics.get("sample_count", len(videos))
        avg_views = analytics.get("avg_views", analytics.get("avg_views_10", 0))
        total_views = analytics.get("total_views", analytics.get("total_views_10", 0))
        max_v = analytics.get("max_view", analytics.get("max_view_10", 0))
        min_v = analytics.get("min_view", analytics.get("min_view_10", 0))

        # 1. Update Kartu Metrik
        self.title_avg_view.config(text=f"⭐ RATA-RATA VIEW ({sample_count} VIDEO)")
        self.val_avg_view.config(text=format_number(avg_views))
        self.sub_avg_view.config(text=f"Total: {format_number(total_views)} views ({sample_count} video)")

        fav_session = analytics.get("most_active_session", "-").split()[0]
        self.val_freq.config(text=f"{analytics.get('avg_interval_days', 0):.1f} Hari")
        self.sub_freq.config(text=f"{analytics.get('freq_text', '-')} | Jam: {fav_session}")

        avg_dur_str = format_duration(analytics.get("avg_duration", 0))
        self.title_peak.config(text=f"🏆 VIEW TERTINGGI ({sample_count} VIDEO)")
        self.val_peak.config(text=format_number(max_v))
        self.sub_peak.config(text=f"Min: {format_number(min_v)} | Rerata durasi: {avg_dur_str}")

        followers = profile.get("followerCount", 0)
        self.val_profile_stat.config(text=f"{format_number(followers)} Fans")
        self.sub_profile_stat.config(text=f"{format_number(profile.get('heartCount', 0))} Total Suka | {profile.get('videoCount', 0)} Video")

        # Update Judul Tab Notebook
        self.notebook.tab(0, text=f"  📈 Grafik Views ({sample_count} Video Terakhir)  ")
        self.notebook.tab(2, text=f"  📋 Tabel {sample_count} Video Terakhir  ")

        # 2. Update Tabel Video Sesuai sample_count
        for row in self.tree.get_children():
            self.tree.delete(row)

        analyzed_vids = analytics.get("analyzed_videos", videos[:sample_count])
        for i, v in enumerate(analyzed_vids, start=1):
            dt = v.get("datetime")
            date_str = dt.strftime("%d/%m/%Y") if dt else "-"
            time_str = dt.strftime("%H:%M:%S WIB") if dt else "-"
            dur_str = format_duration(v.get("duration", 0))
            self.tree.insert("", tk.END, values=(
                i,
                date_str,
                time_str,
                dur_str,
                v.get("title", "-"),
                format_full_number(v.get("view_count", 0)),
                format_full_number(v.get("like_count", 0)),
                format_full_number(v.get("comment_count", 0)),
                v.get("url", "-")
            ))

        # 3. Render Grafik Rata-rata Views
        self.render_views_chart(analytics)

        # 4. Render Grafik Frekuensi Unggah
        self.render_frequency_chart(analytics)

        # 5. Update Insight Teks
        self.render_insight_text(profile, analytics)

        demo_tag = " (Mode Demo)" if is_demo else ""
        self.set_loading(False, f"Analisis selesai untuk @{profile.get('username')}{demo_tag}. Menganalisis {len(analyzed_vids)} video.")

    # ==========================================
    # GRAFIK RATA-RATA VIEW VIDEO TERAKHIR
    # ==========================================
    def render_views_chart(self, analytics: Dict[str, Any]):
        """Menggambar grafik batang & garis view video terakhir dengan jam posting dan durasi."""
        for widget in self.tab_views.winfo_children():
            widget.destroy()

        analyzed_vids = analytics.get("analyzed_videos") or analytics.get("last_10", [])
        sample_count = analytics.get("sample_count", len(analyzed_vids))
        if not analyzed_vids:
            lbl = tk.Label(self.tab_views, text="Tidak ada data video untuk ditampilkan.",
                           font=("Segoe UI", 12), fg=COLORS["text_secondary"], bg=COLORS["bg_dark"])
            lbl.pack(expand=True)
            return

        # Urutkan dari video terlama ke terbaru (V-N sampai V-1/Terbaru)
        chronological = list(reversed(analyzed_vids))
        views = [v["view_count"] for v in chronological]
        avg_view = analytics.get("avg_views", analytics.get("avg_views_10", 0))

        # Labels dengan informasi Jam Posting dan Durasi
        labels = []
        n = len(chronological)
        for idx, v in enumerate(chronological):
            dt = v.get("datetime")
            date_short = dt.strftime("%d/%m") if dt else f"#{idx+1}"
            time_short = dt.strftime("%H:%M") if dt else ""
            dur_str = format_duration(v.get("duration", 0))

            if n <= 12:
                info_line = f"{time_short}\n{dur_str}" if time_short else dur_str
                if idx == n - 1:
                    labels.append(f"Terbaru\n{date_short}\n{info_line}")
                else:
                    labels.append(f"V-{n-idx}\n{date_short}\n{info_line}")
            else:
                if idx == n - 1:
                    labels.append(f"Terbaru ({date_short} {time_short})")
                else:
                    labels.append(f"V-{n-idx} ({date_short})")

        # Matplotlib Figure dengan tema gelap
        fig, ax = plt.subplots(figsize=(9, 4.8), dpi=100)
        fig.patch.set_facecolor(COLORS["bg_dark"])
        ax.set_facecolor(COLORS["card_bg"])

        x = range(len(views))
        bars = ax.bar(x, views, color=COLORS["accent_pink"], width=0.58, alpha=0.9, zorder=3, label="Views per Video")

        # Garis Rata-Rata View (Benchmark dinamis)
        line_avg = ax.axhline(avg_view, color=COLORS["accent_cyan"], linestyle="--", linewidth=2.2,
                              zorder=4, label=f"Rata-rata: {format_number(avg_view)} views ({sample_count} Video)")

        # Tambahkan label angka di atas setiap bar
        font_size = 8 if len(views) > 20 else 9
        for bar in bars:
            height = bar.get_height()
            ax.annotate(format_number(height),
                        xy=(bar.get_x() + bar.get_width() / 2, height),
                        xytext=(0, 4),
                        textcoords="offset points",
                        ha="center", va="bottom",
                        fontsize=font_size, fontweight="bold",
                        color=COLORS["text_primary"])

        # Format Axis & Grid
        ax.set_xticks(x)
        rot = 45 if len(views) > 12 else 0
        ax.set_xticklabels(labels, fontsize=8 if len(views) > 12 else 9, color=COLORS["text_secondary"], rotation=rot)
        ax.yaxis.set_major_formatter(ticker.FuncFormatter(lambda y, _: format_number(y)))
        ax.tick_params(colors=COLORS["text_secondary"], labelsize=9)

        ax.grid(axis="y", color=COLORS["card_border"], linestyle=":", linewidth=0.8, alpha=0.7, zorder=0)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.spines["left"].set_color(COLORS["card_border"])
        ax.spines["bottom"].set_color(COLORS["card_border"])

        avg_dur_text = format_duration(analytics.get("avg_duration", 0))
        ax.set_title(f"Analisis Views {sample_count} Video Terakhir vs Rata-Rata | Rerata Durasi: {avg_dur_text}",
                     fontsize=12, fontweight="bold", color=COLORS["text_primary"], pad=14)
        ax.set_ylabel("Jumlah Tayangan (Views)", fontsize=10, color=COLORS["text_secondary"])

        # Legend elegan
        ax.legend(facecolor=COLORS["card_alt"], edgecolor=COLORS["card_border"],
                  labelcolor=COLORS["text_primary"], loc="upper left", fontsize=9)

        # Matplotlib Canvas di Tkinter
        canvas = FigureCanvasTkAgg(fig, master=self.tab_views)
        canvas.draw()
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Toolbar Navigasi
        toolbar = NavigationToolbar2Tk(canvas, self.tab_views)
        toolbar.config(background=COLORS["card_bg"])
        toolbar.update()

    # ==========================================
    # GRAFIK FREKUENSI UNGGAH & WAKTU POSTING
    # ==========================================
    def render_frequency_chart(self, analytics: Dict[str, Any]):
        """Menggambar 3 grafik untuk frekuensi unggah: Timeline interval, Distribusi hari, dan Jam posting."""
        for widget in self.tab_freq.winfo_children():
            widget.destroy()

        intervals = analytics.get("intervals_days", [])
        day_counts = analytics.get("day_counts", {})
        sorted_dates = analytics.get("valid_dates_sorted", [])
        hour_sessions = analytics.get("hour_sessions", {})

        if not sorted_dates or len(sorted_dates) < 2:
            lbl = tk.Label(self.tab_freq, text="Data unggahan belum cukup untuk membuat grafik frekuensi.",
                           font=("Segoe UI", 12), fg=COLORS["text_secondary"], bg=COLORS["bg_dark"])
            lbl.pack(expand=True)
            return

        fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(12.5, 4.8), dpi=100)
        fig.patch.set_facecolor(COLORS["bg_dark"])

        # Subplot 1: Jeda Waktu Antar Unggahan (Interval Hari)
        ax1.set_facecolor(COLORS["card_bg"])
        idx_intervals = range(1, len(intervals) + 1)
        ax1.plot(idx_intervals, intervals, marker="o", color=COLORS["accent_cyan"],
                 linewidth=2.2, markersize=6, label="Interval (Hari)", zorder=3)

        avg_interval = analytics.get("avg_interval_days", 0)
        ax1.axhline(avg_interval, color=COLORS["accent_yellow"], linestyle="--", linewidth=1.8,
                    label=f"Rata-rata: {avg_interval:.1f} hari", zorder=4)

        ax1.fill_between(idx_intervals, intervals, alpha=0.15, color=COLORS["accent_cyan"])

        ax1.set_title("Konsistensi Jeda Antar Unggahan", fontsize=11, fontweight="bold",
                      color=COLORS["text_primary"], pad=12)
        ax1.set_xlabel("Urutan Transisi Video", fontsize=9, color=COLORS["text_secondary"])
        ax1.set_ylabel("Jeda Waktu (Hari)", fontsize=9, color=COLORS["text_secondary"])
        ax1.tick_params(colors=COLORS["text_secondary"], labelsize=8)
        ax1.grid(color=COLORS["card_border"], linestyle=":", linewidth=0.8, alpha=0.7)
        ax1.legend(facecolor=COLORS["card_alt"], edgecolor=COLORS["card_border"],
                   labelcolor=COLORS["text_primary"], fontsize=8)

        for spine in ["top", "right"]:
            ax1.spines[spine].set_visible(False)
        ax1.spines["left"].set_color(COLORS["card_border"])
        ax1.spines["bottom"].set_color(COLORS["card_border"])

        # Subplot 2: Frekuensi Upload Berdasarkan Hari dalam Seminggu
        ax2.set_facecolor(COLORS["card_bg"])
        days = list(day_counts.keys())
        counts = list(day_counts.values())

        max_c = max(counts) if counts else 0
        bar_colors = [COLORS["accent_pink"] if c == max_c and c > 0 else COLORS["accent_purple"] for c in counts]

        bars = ax2.bar(days, counts, color=bar_colors, width=0.6, zorder=3)

        for bar in bars:
            h = bar.get_height()
            if h > 0:
                ax2.annotate(str(int(h)),
                             xy=(bar.get_x() + bar.get_width() / 2, h),
                             xytext=(0, 3), textcoords="offset points",
                             ha="center", va="bottom",
                             fontsize=8, fontweight="bold", color=COLORS["text_primary"])

        ax2.set_title("Distribusi Hari Unggahan", fontsize=11, fontweight="bold",
                      color=COLORS["text_primary"], pad=12)
        ax2.set_ylabel("Jumlah Video", fontsize=9, color=COLORS["text_secondary"])
        ax2.tick_params(colors=COLORS["text_secondary"], labelsize=8)
        ax2.grid(axis="y", color=COLORS["card_border"], linestyle=":", linewidth=0.8, alpha=0.7)

        for spine in ["top", "right"]:
            ax2.spines[spine].set_visible(False)
        ax2.spines["left"].set_color(COLORS["card_border"])
        ax2.spines["bottom"].set_color(COLORS["card_border"])

        # Subplot 3: Waktu Jam Posting (Berdasarkan Sesi Jam)
        ax3.set_facecolor(COLORS["card_bg"])
        session_names = ["Pagi\n05-11", "Siang\n11-15", "Sore\n15-18", "Malam\n18-24", "Dini Hari\n00-05"]
        session_keys = ["Pagi (05-11)", "Siang (11-15)", "Sore (15-18)", "Malam (18-24)", "Dini Hari (00-05)"]
        session_counts = [hour_sessions.get(k, 0) for k in session_keys]

        max_s = max(session_counts) if session_counts else 0
        s_colors = [COLORS["accent_pink"] if sc == max_s and sc > 0 else COLORS["accent_cyan"] for sc in session_counts]

        bars3 = ax3.bar(session_names, session_counts, color=s_colors, width=0.6, zorder=3)

        for bar in bars3:
            h = bar.get_height()
            if h > 0:
                ax3.annotate(str(int(h)),
                             xy=(bar.get_x() + bar.get_width() / 2, h),
                             xytext=(0, 3), textcoords="offset points",
                             ha="center", va="bottom",
                             fontsize=8, fontweight="bold", color=COLORS["text_primary"])

        ax3.set_title("Waktu Jam Posting (Sesi)", fontsize=11, fontweight="bold",
                      color=COLORS["text_primary"], pad=12)
        ax3.set_ylabel("Jumlah Video", fontsize=9, color=COLORS["text_secondary"])
        ax3.tick_params(colors=COLORS["text_secondary"], labelsize=8)
        ax3.grid(axis="y", color=COLORS["card_border"], linestyle=":", linewidth=0.8, alpha=0.7)

        for spine in ["top", "right"]:
            ax3.spines[spine].set_visible(False)
        ax3.spines["left"].set_color(COLORS["card_border"])
        ax3.spines["bottom"].set_color(COLORS["card_border"])

        fig.tight_layout()

        canvas = FigureCanvasTkAgg(fig, master=self.tab_freq)
        canvas.draw()
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        toolbar = NavigationToolbar2Tk(canvas, self.tab_freq)
        toolbar.config(background=COLORS["card_bg"])
        toolbar.update()

    # ==========================================
    # INSIGHT & ANALISIS TEKS
    # ==========================================
    def render_insight_text(self, profile: Dict[str, Any], analytics: Dict[str, Any]):
        """Menghasilkan teks rangkuman analitik komprehensif sesuai jumlah sampel video."""
        sample_count = analytics.get("sample_count", 10)
        avg_views = analytics.get("avg_views", analytics.get("avg_views_10", 0))
        total_views = analytics.get("total_views", analytics.get("total_views_10", 0))
        max_view = analytics.get("max_view", analytics.get("max_view_10", 0))
        min_view = analytics.get("min_view", analytics.get("min_view_10", 0))
        avg_likes = analytics.get("avg_likes", analytics.get("avg_likes_10", 0))
        avg_interval = analytics.get("avg_interval_days", 0)
        freq_text = analytics.get("freq_text", "-")
        most_active_day = analytics.get("most_active_day", "-")

        # Metrik Durasi & Jam Posting
        avg_dur = analytics.get("avg_duration", 0)
        max_dur = analytics.get("max_duration", 0)
        min_dur = analytics.get("min_duration", 0)
        most_common_hr = analytics.get("most_common_hour")
        hr_str = f"Pukul {most_common_hr:02d}:00 WIB" if most_common_hr is not None else "Bervariasi"
        most_active_session = analytics.get("most_active_session", "-")

        if avg_dur <= 20:
            dur_type = "Format Sangat Singkat / Micro-Shorts (< 20 detik)"
        elif avg_dur <= 60:
            dur_type = "Format Standar Shorts (20 - 60 detik) - Ideal untuk retensi algoritma"
        elif avg_dur <= 180:
            dur_type = "Format Menengah (1 - 3 menit) - Konten Edukasi & Storytelling"
        else:
            dur_type = "Format Panjang (> 3 menit) - Konten In-Depth / Vlog"

        # Rasio Engagement (Likes / Views)
        eng_rate = (avg_likes / avg_views * 100) if avg_views > 0 else 0

        # Penilaian Konsistensi
        if avg_interval <= 2.0:
            konsistensi = "Sangat Tinggi (Akun aktif hampir setiap hari)"
        elif avg_interval <= 4.0:
            konsistensi = "Stabil & Teratur (2-3 video per minggu)"
        elif avg_interval <= 7.0:
            konsistensi = "Cukup Teratur (~1 video per minggu)"
        else:
            konsistensi = "Rendah / Fluktuatif (Jeda panjang antar unggahan)"

        text = f"""========================================================================
RINGKASAN ANALISIS AKUN: @{profile.get('username')} ({profile.get('nickname')})
Waktu Analisis: {datetime.datetime.now().strftime('%d %B %Y, %H:%M:%S')}
Sampel Dianalisis: {sample_count} Video Terakhir
========================================================================

1. METRIK RATA-RATA VIEW {sample_count} VIDEO TERAKHIR:
------------------------------------------------------------------------
   • Rata-rata Views ({sample_count} Terakhir) : {format_full_number(int(avg_views))} views ({format_number(avg_views)})
   • Total Akumulasi Views         : {format_full_number(int(total_views))} views ({sample_count} video)
   • Video Views Tertinggi (Peak)  : {format_full_number(int(max_view))} views ({format_number(max_view)})
   • Video Views Terendah          : {format_full_number(int(min_view))} views ({format_number(min_view)})
   • Rata-rata Likes               : {format_full_number(int(avg_likes))} likes
   • Engagement Rate (Likes/Views) : {eng_rate:.2f}% (Rata-rata industri: 4% - 8%)

2. POLA & FREKUENSI UNGGAHAN:
------------------------------------------------------------------------
   • Rata-rata Jeda Antar Video    : {avg_interval:.2f} hari
   • Pola Jadwal Unggahan          : {freq_text}
   • Level Konsistensi Akun        : {konsistensi}
   • Hari Terbanyak Mengunggah     : Hari {most_active_day}

3. ANALISIS WAKTU POSTING & DURASI VIDEO:
------------------------------------------------------------------------
   • Jam Posting Paling Sering     : {hr_str} ({most_active_session})
   • Sesi Unggah Dominan           : Sesi {most_active_session}
   • Rata-rata Durasi Video        : {format_duration(avg_dur)} ({int(round(avg_dur))} detik)
   • Video Terpanjang (Max)        : {format_duration(max_dur)} ({int(round(max_dur))} detik)
   • Video Terpendek (Min)         : {format_duration(min_dur)} ({int(round(min_dur))} detik)
   • Karakteristik Format Konten   : {dur_type}

4. INFORMASI PROFIL:
------------------------------------------------------------------------
   • Total Followers               : {format_full_number(profile.get('followerCount', 0))}
   • Total Suka Akun               : {format_full_number(profile.get('heartCount', 0))}
   • Total Video Publik            : {profile.get('videoCount', 0)} video
   • Bio / Signature               : {profile.get('signature') or '-'}

5. KESIMPULAN & REKOMENDASI:
------------------------------------------------------------------------
   [+] Kinerja Tayangan:
       Rata-rata {format_number(avg_views)} tayangan per video pada {sample_count} video terakhir menunjukkan akun ini
       memiliki basis penonton aktif sebesar ~{(avg_views / max(profile.get('followerCount', 1), 1) * 100):.1f}% dari total followers.

   [+] Pola Konsistensi & Waktu Posting:
       Akun ini paling optimal mengunggah pada hari {most_active_day} pada sesi {most_active_session}.
       Pertahankan durasi konten di kisaran {format_duration(avg_dur)} dengan ritme posting {freq_text}
       untuk memaksimalkan retensi audiens TikTok.
"""
        self.txt_insight.config(state=tk.NORMAL)
        self.txt_insight.delete("1.0", tk.END)
        self.txt_insight.insert(tk.END, text)
        self.txt_insight.config(state=tk.DISABLED)


# ==========================================
# MAIN ENTRY POINT
# ==========================================
if __name__ == "__main__":
    app = TikTokAnalyticsApp()
    app.mainloop()
