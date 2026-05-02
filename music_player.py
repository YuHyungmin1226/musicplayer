import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
import random
import time
import sys
from PIL import Image, ImageTk

# --- Library Check ---
try:
    import pygame
    from mutagen import File as MutagenFile
except ImportError as e:
    # GUI error message if dependencies are missing
    root = tk.Tk()
    root.withdraw()
    missing_module = str(e).split("'")[-2] if "'" in str(e) else "Required modules"
    messagebox.showerror("Dependency Error", 
        f"{missing_module} module not found.\n\n"
        "Please ensure all dependencies are installed.\n"
        "Run: pip install -r requirements.txt")
    root.destroy()
    exit(1)

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

class MusicEngine:
    """Handles playback logic and state."""
    def __init__(self):
        if not pygame.mixer.get_init():
            pygame.mixer.pre_init(44100, -16, 2, 4096)
        pygame.mixer.init()
        self.playlist = []
        self.original_playlist = []
        self.current_index = -1
        self.is_paused = False
        self.is_stopped = True
        self.shuffle_mode = False
        self.repeat_mode = "NONE" # NONE, ONE, ALL
        self.volume = 0.5
        self.start_time = 0 # Used for seeking calculation
        self.duration_cache = {} # Cache for song lengths
        
    def add_songs(self, file_paths):
        for path in file_paths:
            if path not in self.playlist:
                self.playlist.append(path)
        return len(file_paths)

    def load_folder(self, folder_path):
        added_count = 0
        for root, dirs, files in os.walk(folder_path):
            for file in files:
                if file.lower().endswith((".mp3", ".ogg", ".wav", ".flac")):
                    full_path = os.path.join(root, file)
                    if full_path not in self.playlist:
                        self.playlist.append(full_path)
                        added_count += 1
        return added_count

    def play(self, index=None, start_pos=0):
        if not self.playlist:
            return False
        
        if index is not None:
            self.current_index = index
        elif self.current_index == -1:
            self.current_index = 0
            
        song_path = self.playlist[self.current_index]
        try:
            pygame.mixer.music.load(song_path)
            pygame.mixer.music.set_volume(self.volume)
            pygame.mixer.music.play(start=start_pos)
            self.start_time = start_pos
            self.is_paused = False
            self.is_stopped = False
            return True
        except Exception as e:
            print(f"Playback error: {e}")
            return False

    def stop(self):
        pygame.mixer.music.stop()
        self.is_paused = False
        self.is_stopped = True
        self.start_time = 0

    def pause_resume(self):
        if not pygame.mixer.music.get_busy() and not self.is_paused:
            return
        
        if self.is_paused:
            pygame.mixer.music.unpause()
            self.is_paused = False
        else:
            pygame.mixer.music.pause()
            self.is_paused = True
        return self.is_paused

    def next_song(self):
        if not self.playlist: return None
        if self.shuffle_mode:
            self.current_index = random.randint(0, len(self.playlist) - 1)
        else:
            self.current_index = (self.current_index + 1) % len(self.playlist)
        return self.current_index

    def prev_song(self):
        if not self.playlist: return None
        if self.shuffle_mode:
            self.current_index = random.randint(0, len(self.playlist) - 1)
        else:
            self.current_index = (self.current_index - 1) % len(self.playlist)
        return self.current_index

    def set_volume(self, val):
        self.volume = float(val)
        pygame.mixer.music.set_volume(self.volume)

    def toggle_shuffle(self):
        self.shuffle_mode = not self.shuffle_mode
        return self.shuffle_mode

    def get_current_pos(self):
        if not pygame.mixer.music.get_busy() and not self.is_paused:
            return 0
        return self.start_time + (pygame.mixer.music.get_pos() / 1000)

    def get_song_length(self):
        if self.current_index == -1: return 0
        path = self.playlist[self.current_index]
        if path in self.duration_cache:
            return self.duration_cache[path]
        try:
            audio = MutagenFile(path)
            if audio is not None and audio.info:
                length = audio.info.length
                self.duration_cache[path] = length
                return length
            s = pygame.mixer.Sound(path)
            length = s.get_length()
            self.duration_cache[path] = length
            return length
        except Exception as e:
            return 0

class MusicPlayerUI(tk.Tk):
    def __init__(self, engine):
        super().__init__()
        self.engine = engine
        self.title("Antigravity Music Player")
        self.geometry("900x700")
        self.configure(bg="#121212")
        
        # Colors
        self.colors = {
            "bg": "#121212",
            "sidebar": "#000000",
            "accent": "#1DB954",
            "text_primary": "#FFFFFF",
            "text_secondary": "#B3B3B3",
            "card": "#1E1E1E",
            "hover": "#282828"
        }

        self.setup_styles()
        self.create_widgets()
        self.update_loop()

    def setup_styles(self):
        self.style = ttk.Style()
        self.style.theme_use('clam')
        
        self.style.configure("TFrame", background=self.colors["bg"])
        self.style.configure("Sidebar.TFrame", background=self.colors["sidebar"])
        self.style.configure("Card.TFrame", background=self.colors["card"])
        
        self.style.configure("TLabel", background=self.colors["bg"], foreground=self.colors["text_primary"], font=("Helvetica", 11))
        self.style.configure("Title.TLabel", font=("Helvetica", 18, "bold"))
        self.style.configure("Artist.TLabel", foreground=self.colors["text_secondary"], font=("Helvetica", 12))
        
        # Custom Scale (Progress Bar)
        self.style.configure("Custom.Horizontal.TScale", 
                           background=self.colors["bg"], 
                           troughcolor=self.colors["card"],
                           lightcolor=self.colors["accent"],
                           darkcolor=self.colors["accent"])

    def create_widgets(self):
        # --- Main Layout ---
        self.main_container = ttk.Frame(self)
        self.main_container.pack(fill="both", expand=True)

        # 1. Sidebar (Playlist)
        self.sidebar = ttk.Frame(self.main_container, style="Sidebar.TFrame", width=300)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)

        ttk.Label(self.sidebar, text="Your Library", font=("Helvetica", 14, "bold"), 
                  background=self.colors["sidebar"]).pack(pady=20, padx=20, anchor="w")

        self.playlist_box = tk.Listbox(self.sidebar, 
                                     bg=self.colors["sidebar"], 
                                     fg=self.colors["text_secondary"],
                                     selectbackground=self.colors["hover"],
                                     selectforeground=self.colors["text_primary"],
                                     font=("Helvetica", 11), borderwidth=0, 
                                     highlightthickness=0, activestyle="none")
        self.playlist_box.pack(fill="both", expand=True, padx=10, pady=10)
        self.playlist_box.bind("<Double-1>", self.play_selected)

        # 2. Main Content Area
        self.content = ttk.Frame(self.main_container)
        self.content.pack(side="right", fill="both", expand=True)

        # Album Art
        self.art_frame = ttk.Frame(self.content)
        self.art_frame.pack(pady=40)
        
        try:
            art_path = resource_path("assets/default_art.png")
            img = Image.open(art_path)
            img = img.resize((350, 350), Image.Resampling.LANCZOS)
            self.album_art = ImageTk.PhotoImage(img)
            self.art_label = tk.Label(self.art_frame, image=self.album_art, bg=self.colors["bg"], borderwidth=0)
            self.art_label.pack()
        except Exception as e:
            print(f"Error loading art: {e}")
            self.art_label = ttk.Label(self.art_frame, text="[ Album Art ]")
            self.art_label.pack()

        # Song Info
        self.info_frame = ttk.Frame(self.content)
        self.info_frame.pack(fill="x", padx=40)
        
        self.song_label = ttk.Label(self.info_frame, text="No song selected", style="Title.TLabel")
        self.song_label.pack(anchor="center")
        
        self.artist_label = ttk.Label(self.info_frame, text="Unknown Artist", style="Artist.TLabel")
        self.artist_label.pack(anchor="center", pady=(5, 20))

        # 3. Bottom Player Bar
        self.player_bar = tk.Frame(self, bg=self.colors["card"], height=100)
        self.player_bar.pack(side="bottom", fill="x")
        self.player_bar.pack_propagate(False)

        # Controls Container
        self.controls_frame = tk.Frame(self.player_bar, bg=self.colors["card"])
        self.controls_frame.pack(expand=True)

        # Progress
        self.progress_frame = tk.Frame(self.player_bar, bg=self.colors["card"])
        self.progress_frame.pack(fill="x", padx=20)
        
        self.time_start = tk.Label(self.progress_frame, text="0:00", bg=self.colors["card"], fg=self.colors["text_secondary"], font=("Helvetica", 9))
        self.time_start.pack(side="left")
        
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Scale(self.progress_frame, orient="horizontal", variable=self.progress_var, from_=0, to=100, style="Custom.Horizontal.TScale", command=self.on_seek_drag)
        self.progress_bar.pack(side="left", fill="x", expand=True, padx=10)
        self.progress_bar.bind("<ButtonRelease-1>", self.on_seek_release)
        
        self.time_end = tk.Label(self.progress_frame, text="0:00", bg=self.colors["card"], fg=self.colors["text_secondary"], font=("Helvetica", 9))
        self.time_end.pack(side="right")

        # Buttons
        btn_opts = {"bg": self.colors["card"], "fg": self.colors["text_primary"], "borderwidth": 0, "activebackground": self.colors["hover"], "font": ("Helvetica", 20)}
        
        self.shuffle_btn = tk.Button(self.controls_frame, text="⇄", command=self.toggle_shuffle, **btn_opts, font=("Helvetica", 14))
        self.shuffle_btn.pack(side="left", padx=15)
        
        tk.Button(self.controls_frame, text="⏮", command=self.prev_song, **btn_opts).pack(side="left", padx=10)
        
        self.play_btn = tk.Button(self.controls_frame, text="▶", command=self.toggle_play, **btn_opts, font=("Helvetica", 24))
        self.play_btn.pack(side="left", padx=15)
        
        tk.Button(self.controls_frame, text="⏭", command=self.next_song, **btn_opts).pack(side="left", padx=10)
        
        self.repeat_btn = tk.Button(self.controls_frame, text="↻", command=self.toggle_repeat, **btn_opts, font=("Helvetica", 14))
        self.repeat_btn.pack(side="left", padx=15)

        # Volume
        self.vol_frame = tk.Frame(self.player_bar, bg=self.colors["card"])
        self.vol_frame.place(relx=0.85, rely=0.5, anchor="center")
        
        tk.Label(self.vol_frame, text="Speaker", bg=self.colors["card"], fg=self.colors["text_secondary"]).pack(side="left", padx=5)
        self.volume_slider = ttk.Scale(self.vol_frame, from_=0, to=1, orient="horizontal", style="Custom.Horizontal.TScale", command=self.engine.set_volume, length=100)
        self.volume_slider.set(0.5)
        self.volume_slider.pack(side="left")

        # Menu
        self.create_menu()

    def create_menu(self):
        menubar = tk.Menu(self)
        file_menu = tk.Menu(menubar, tearoff=0, bg=self.colors["card"], fg=self.colors["text_primary"])
        file_menu.add_command(label="Add Files", command=self.add_files)
        file_menu.add_command(label="Add Folder", command=self.add_folder)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.destroy)
        menubar.add_cascade(label="File", menu=file_menu)
        self.config(menu=menubar)

    def add_files(self):
        files = filedialog.askopenfilenames(filetypes=[("Audio Files", "*.mp3 *.ogg *.wav *.flac")])
        if files:
            self.engine.add_songs(files)
            self.update_listbox()

    def add_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.engine.load_folder(folder)
            self.update_listbox()

    def update_listbox(self):
        self.playlist_box.delete(0, tk.END)
        for path in self.engine.playlist:
            self.playlist_box.insert(tk.END, f"  {os.path.basename(path)}")

    def play_selected(self, event=None):
        selection = self.playlist_box.curselection()
        if selection:
            self.engine.play(index=selection[0])
            self.update_ui_state()

    def toggle_play(self):
        if self.engine.is_stopped:
            if self.engine.playlist:
                self.engine.play(self.engine.current_index if self.engine.current_index != -1 else 0)
        elif self.engine.current_index == -1 and self.engine.playlist:
            self.engine.play(0)
        else:
            self.engine.pause_resume()
        self.update_ui_state()

    def stop_song(self):
        self.engine.stop()
        self.update_ui_state()

    def next_song(self):
        if not self.engine.playlist: return
        should_play = not self.engine.is_paused and not self.engine.is_stopped
        self.engine.next_song()
        if should_play:
            self.engine.play()
        self.update_ui_state()

    def prev_song(self):
        if not self.engine.playlist: return
        should_play = not self.engine.is_paused and not self.engine.is_stopped
        self.engine.prev_song()
        if should_play:
            self.engine.play()
        self.update_ui_state()

    def toggle_shuffle(self):
        is_on = self.engine.toggle_shuffle()
        self.shuffle_btn.config(fg=self.colors["accent"] if is_on else self.colors["text_primary"])

    def toggle_repeat(self):
        modes = ["NONE", "ONE", "ALL"]
        current = modes.index(self.engine.repeat_mode)
        next_mode = modes[(current + 1) % len(modes)]
        self.engine.repeat_mode = next_mode
        self.repeat_btn.config(fg=self.colors["accent"] if next_mode != "NONE" else self.colors["text_primary"])

    def on_seek_drag(self, val):
        self.is_dragging = True

    def on_seek_release(self, event):
        if self.engine.current_index != -1:
            total = self.engine.get_song_length()
            target_time = (self.progress_var.get() / 100) * total
            self.engine.play(start_pos=target_time)
        self.is_dragging = False

    def format_time(self, seconds):
        mins, secs = divmod(int(seconds), 60)
        return f"{mins}:{secs:02d}"

    def update_ui_state(self):
        if self.engine.current_index != -1:
            song_name = os.path.basename(self.engine.playlist[self.engine.current_index])
            self.song_label.config(text=song_name)
            self.playlist_box.selection_clear(0, tk.END)
            self.playlist_box.selection_set(self.engine.current_index)
            self.playlist_box.see(self.engine.current_index)
            self.play_btn.config(text="⏸" if not self.engine.is_paused and not self.engine.is_stopped else "▶")

    def update_loop(self):
        if self.engine.current_index != -1:
            current_pos = self.engine.get_current_pos()
            total_len = self.engine.get_song_length()
            
            if not getattr(self, 'is_dragging', False):
                if total_len > 0:
                    self.progress_var.set((current_pos / total_len) * 100)
                else:
                    self.progress_var.set(0)
            
            self.time_start.config(text=self.format_time(current_pos))
            self.time_end.config(text=self.format_time(total_len))

            # Auto next song
            if not pygame.mixer.music.get_busy() and not self.engine.is_paused and not self.engine.is_stopped:
                if self.engine.repeat_mode == "ONE":
                    self.engine.play(self.engine.current_index)
                elif self.engine.repeat_mode == "ALL" or self.engine.current_index < len(self.engine.playlist) - 1:
                    self.next_song()
                    self.engine.play() # Auto-play next song
                    self.update_ui_state()
                else:
                    self.engine.stop()
                    self.update_ui_state()

        self.after(500, self.update_loop)

if __name__ == "__main__":
    engine = MusicEngine()
    app = MusicPlayerUI(engine)
    app.mainloop()
