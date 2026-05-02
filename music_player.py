import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
import random
import time

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

class MusicEngine:
    """Handles playback logic and state."""
    def __init__(self):
        # Pre-initialize mixer with better buffer for high-quality audio
        if not pygame.mixer.get_init():
            pygame.mixer.pre_init(44100, -16, 2, 4096)
        pygame.mixer.init()
        self.playlist = []
        self.original_playlist = []
        self.current_index = -1
        self.is_paused = False
        self.shuffle_mode = False
        self.repeat_mode = "NONE" # NONE, ONE, ALL
        self.volume = 0.5
        self.start_time = 0 # Used for seeking calculation
        self.duration_cache = {} # Cache for song lengths
        
    def add_songs(self, file_paths):
        for path in file_paths:
            if path not in self.original_playlist:
                self.playlist.append(path)
                self.original_playlist.append(path)
        return len(file_paths)

    def load_folder(self, folder_path):
        added_count = 0
        for root, dirs, files in os.walk(folder_path):
            for file in files:
                if file.lower().endswith((".mp3", ".ogg", ".wav", ".flac")):
                    full_path = os.path.join(root, file)
                    if full_path not in self.original_playlist:
                        self.playlist.append(full_path)
                        self.original_playlist.append(full_path)
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
            return True
        except Exception as e:
            print(f"Playback error: {e}")
            return False

    def stop(self):
        pygame.mixer.music.stop()
        self.is_paused = False
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
        self.play()
        return self.current_index

    def prev_song(self):
        if not self.playlist: return None
        if self.shuffle_mode:
            self.current_index = random.randint(0, len(self.playlist) - 1)
        else:
            self.current_index = (self.current_index - 1) % len(self.playlist)
        self.play()
        return self.current_index

    def set_volume(self, val):
        self.volume = float(val)
        pygame.mixer.music.set_volume(self.volume)

    def toggle_shuffle(self):
        self.shuffle_mode = not self.shuffle_mode
        if self.shuffle_mode:
            current_song = self.playlist[self.current_index] if self.current_index != -1 else None
            random.shuffle(self.playlist)
            if current_song:
                self.current_index = self.playlist.index(current_song)
        else:
            current_song = self.playlist[self.current_index] if self.current_index != -1 else None
            self.playlist = list(self.original_playlist)
            if current_song:
                self.current_index = self.playlist.index(current_song)
        return self.shuffle_mode

    def get_current_pos(self):
        if not pygame.mixer.music.get_busy() and not self.is_paused:
            return 0
        # get_pos returns ms since play() was called
        return self.start_time + (pygame.mixer.music.get_pos() / 1000)

    def get_song_length(self):
        if self.current_index == -1: return 0
        path = self.playlist[self.current_index]
        
        # Check cache first
        if path in self.duration_cache:
            return self.duration_cache[path]
            
        try:
            # Use mutagen to get duration without loading the whole file
            audio = MutagenFile(path)
            if audio is not None and audio.info:
                length = audio.info.length
                self.duration_cache[path] = length
                return length
            
            # Fallback to pygame.mixer.Sound (slow, but works for odd files)
            # We cache it so we only do this once
            s = pygame.mixer.Sound(path)
            length = s.get_length()
            self.duration_cache[path] = length
            return length
        except Exception as e:
            print(f"Error getting duration: {e}")
            return 0

class MusicPlayerUI(tk.Tk):
    def __init__(self, engine):
        super().__init__()
        self.engine = engine
        self.title("Modern Music Player")
        self.geometry("800x600")
        self.configure(bg="#f0f0f0")
        
        self.setup_styles()
        self.create_widgets()
        self.update_loop()

    def setup_styles(self):
        self.style = ttk.Style()
        # Use 'aqua' on Mac if possible, else 'clam'
        current_theme = self.style.theme_use()
        if 'aqua' in self.style.theme_names():
            self.style.theme_use('aqua')
            
        self.style.configure("TFrame", background="#f0f0f0")
        self.style.configure("TLabel", background="#f0f0f0", font=("Helvetica", 11))
        self.style.configure("Header.TLabel", font=("Helvetica", 14, "bold"))
        self.style.configure("Controls.TButton", font=("Helvetica", 16))

    def create_widgets(self):
        # --- Top Info Section ---
        top_frame = ttk.Frame(self, padding=20)
        top_frame.pack(fill="x")

        self.song_label = ttk.Label(top_frame, text="No song selected", style="Header.TLabel")
        self.song_label.pack(pady=(0, 10))

        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Scale(top_frame, orient="horizontal", variable=self.progress_var, from_=0, to=100, command=self.on_seek_drag)
        self.progress_bar.pack(fill="x", pady=5)
        self.progress_bar.bind("<ButtonRelease-1>", self.on_seek_release)
        self.is_dragging = False

        self.time_label = ttk.Label(top_frame, text="00:00 / 00:00")
        self.time_label.pack()

        # --- Middle Playlist Section ---
        middle_frame = ttk.Frame(self, padding=10)
        middle_frame.pack(fill="both", expand=True)

        self.playlist_box = tk.Listbox(middle_frame, 
                                     bg="white", fg="#333", 
                                     selectbackground="#007aff", selectforeground="white",
                                     font=("Helvetica", 12), borderwidth=0, highlightthickness=1)
        self.playlist_box.pack(side="left", fill="both", expand=True)
        self.playlist_box.bind("<Double-1>", self.play_selected)

        scrollbar = ttk.Scrollbar(middle_frame, orient="vertical", command=self.playlist_box.yview)
        scrollbar.pack(side="right", fill="y")
        self.playlist_box.config(yscrollcommand=scrollbar.set)

        # --- Bottom Control Section ---
        bottom_frame = ttk.Frame(self, padding=20)
        bottom_frame.pack(fill="x")

        controls_inner = ttk.Frame(bottom_frame)
        controls_inner.pack()

        ttk.Button(controls_inner, text="⏮", width=5, command=self.prev_song).pack(side="left", padx=5)
        self.play_btn = ttk.Button(controls_inner, text="▶", width=5, command=self.toggle_play)
        self.play_btn.pack(side="left", padx=5)
        ttk.Button(controls_inner, text="⏹", width=5, command=self.stop_song).pack(side="left", padx=5)
        ttk.Button(controls_inner, text="⏭", width=5, command=self.next_song).pack(side="left", padx=5)

        # --- Settings (Volume, Modes) ---
        settings_frame = ttk.Frame(bottom_frame)
        settings_frame.pack(fill="x", pady=(15, 0))

        ttk.Label(settings_frame, text="Volume:").pack(side="left", padx=(0, 10))
        self.volume_slider = ttk.Scale(settings_frame, from_=0, to=1, orient="horizontal", command=self.engine.set_volume)
        self.volume_slider.set(0.5)
        self.volume_slider.pack(side="left", fill="x", expand=True, padx=(0, 20))

        self.shuffle_btn = ttk.Button(settings_frame, text="Shuffle: OFF", command=self.toggle_shuffle)
        self.shuffle_btn.pack(side="left", padx=5)
        
        self.repeat_btn = ttk.Button(settings_frame, text="Repeat: OFF", command=self.toggle_repeat)
        self.repeat_btn.pack(side="left", padx=5)

        # Menu
        menubar = tk.Menu(self)
        file_menu = tk.Menu(menubar, tearoff=0)
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
            self.playlist_box.insert(tk.END, os.path.basename(path))

    def play_selected(self, event=None):
        selection = self.playlist_box.curselection()
        if selection:
            self.engine.play(index=selection[0])
            self.update_ui_state()

    def toggle_play(self):
        if self.engine.current_index == -1 and self.engine.playlist:
            self.engine.play(0)
        else:
            paused = self.engine.pause_resume()
            self.play_btn.config(text="▶" if paused else "⏸")
        self.update_ui_state()

    def stop_song(self):
        self.engine.stop()
        self.play_btn.config(text="▶")
        self.update_ui_state()

    def next_song(self):
        self.engine.next_song()
        self.update_ui_state()

    def prev_song(self):
        self.engine.prev_song()
        self.update_ui_state()

    def toggle_shuffle(self):
        is_on = self.engine.toggle_shuffle()
        self.shuffle_btn.config(text=f"Shuffle: {'ON' if is_on else 'OFF'}")
        self.update_listbox()

    def toggle_repeat(self):
        modes = ["NONE", "ONE", "ALL"]
        current = modes.index(self.engine.repeat_mode)
        next_mode = modes[(current + 1) % len(modes)]
        self.engine.repeat_mode = next_mode
        self.repeat_btn.config(text=f"Repeat: {next_mode if next_mode != 'NONE' else 'OFF'}")

    def on_seek_drag(self, val):
        self.is_dragging = True

    def on_seek_release(self, event):
        if self.engine.current_index != -1:
            total = self.engine.get_song_length()
            target_time = (self.progress_var.get() / 100) * total
            self.engine.play(start_pos=target_time)
        self.is_dragging = False

    def update_ui_state(self):
        if self.engine.current_index != -1:
            song_name = os.path.basename(self.engine.playlist[self.engine.current_index])
            self.song_label.config(text=song_name)
            self.playlist_box.selection_clear(0, tk.END)
            self.playlist_box.selection_set(self.engine.current_index)
            self.playlist_box.see(self.engine.current_index)
            self.play_btn.config(text="⏸" if not self.engine.is_paused else "▶")

    def format_time(self, seconds):
        mins, secs = divmod(int(seconds), 60)
        return f"{mins:02d}:{secs:02d}"

    def update_loop(self):
        if self.engine.current_index != -1:
            current_pos = self.engine.get_current_pos()
            total_len = self.engine.get_song_length()
            
            if not self.is_dragging:
                if total_len > 0:
                    self.progress_var.set((current_pos / total_len) * 100)
                else:
                    self.progress_var.set(0)
            
            self.time_label.config(text=f"{self.format_time(current_pos)} / {self.format_time(total_len)}")

            # Auto next song
            if not pygame.mixer.music.get_busy() and not self.engine.is_paused:
                if self.engine.repeat_mode == "ONE":
                    self.engine.play(self.engine.current_index)
                elif self.engine.repeat_mode == "ALL" or self.engine.current_index < len(self.engine.playlist) - 1:
                    self.next_song()
                else:
                    self.stop_song()

        self.after(500, self.update_loop)

if __name__ == "__main__":
    engine = MusicEngine()
    app = MusicPlayerUI(engine)
    app.mainloop()
