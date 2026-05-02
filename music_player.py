import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
import random
import time
import sys

# --- Library Check ---
try:
    import pygame
    from mutagen import File as MutagenFile
except ImportError as e:
    root = tk.Tk()
    root.withdraw()
    missing_module = str(e).split("'")[-2] if "'" in str(e) else "Required modules"
    messagebox.showerror("Dependency Error", f"{missing_module} module not found.\n\nRun: pip install -r requirements.txt")
    root.destroy()
    exit(1)

class MusicEngine:
    def __init__(self):
        if not pygame.mixer.get_init():
            pygame.mixer.pre_init(44100, -16, 2, 4096)
        pygame.mixer.init()
        self.playlist = []
        self.current_index = -1
        self.is_paused = False
        self.is_stopped = True
        self.shuffle_mode = False
        self.repeat_mode = "NONE"
        self.volume = 0.5
        self.start_time = 0
        self.duration_cache = {}
        
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
        if not self.playlist: return False
        if index is not None: self.current_index = index
        elif self.current_index == -1: self.current_index = 0
            
        song_path = self.playlist[self.current_index]
        try:
            pygame.mixer.music.load(song_path)
            pygame.mixer.music.set_volume(self.volume)
            pygame.mixer.music.play(start=start_pos)
            self.start_time = start_pos
            self.is_paused = False
            self.is_stopped = False
            return True
        except Exception: return False

    def stop(self):
        pygame.mixer.music.stop()
        self.is_paused = False
        self.is_stopped = True
        self.start_time = 0

    def pause_resume(self):
        if not pygame.mixer.music.get_busy() and not self.is_paused: return
        if self.is_paused:
            pygame.mixer.music.unpause()
            self.is_paused = False
        else:
            pygame.mixer.music.pause()
            self.is_paused = True
        return self.is_paused

    def next_song(self):
        if not self.playlist: return None
        if self.shuffle_mode: self.current_index = random.randint(0, len(self.playlist) - 1)
        else: self.current_index = (self.current_index + 1) % len(self.playlist)
        return self.current_index

    def prev_song(self):
        if not self.playlist: return None
        if self.shuffle_mode: self.current_index = random.randint(0, len(self.playlist) - 1)
        else: self.current_index = (self.current_index - 1) % len(self.playlist)
        return self.current_index

    def set_volume(self, val):
        self.volume = float(val)
        pygame.mixer.music.set_volume(self.volume)

    def toggle_shuffle(self):
        self.shuffle_mode = not self.shuffle_mode
        return self.shuffle_mode

    def get_current_pos(self):
        if not pygame.mixer.music.get_busy() and not self.is_paused: return 0
        return self.start_time + (pygame.mixer.music.get_pos() / 1000)

    def get_song_length(self):
        if self.current_index == -1: return 0
        path = self.playlist[self.current_index]
        if path in self.duration_cache: return self.duration_cache[path]
        try:
            audio = MutagenFile(path)
            if audio and audio.info:
                length = audio.info.length
                self.duration_cache[path] = length
                return length
            s = pygame.mixer.Sound(path)
            length = s.get_length()
            self.duration_cache[path] = length
            return length
        except Exception: return 0

class MusicPlayerUI(tk.Tk):
    def __init__(self, engine):
        super().__init__()
        self.engine = engine
        self.title("Music Player")
        self.geometry("600x500")
        self.create_widgets()
        self.update_loop()

    def create_widgets(self):
        # Top Frame: Info and Progress
        self.top_frame = ttk.Frame(self)
        self.top_frame.pack(fill="x", padx=10, pady=10)

        self.song_label = ttk.Label(self.top_frame, text="No song selected", font=("Helvetica", 12, "bold"))
        self.song_label.pack(pady=5)

        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Scale(self.top_frame, orient="horizontal", variable=self.progress_var, from_=0, to=100, command=self.on_seek_drag)
        self.progress_bar.pack(fill="x", padx=5)
        self.progress_bar.bind("<ButtonRelease-1>", self.on_seek_release)

        self.time_label = ttk.Label(self.top_frame, text="00:00 / 00:00")
        self.time_label.pack(pady=5)

        # Middle Frame: Playlist
        self.middle_frame = ttk.Frame(self)
        self.middle_frame.pack(fill="both", expand=True, padx=10, pady=5)

        self.playlist_box = tk.Listbox(self.middle_frame, selectmode=tk.SINGLE)
        self.playlist_box.pack(side="left", fill="both", expand=True)
        self.playlist_box.bind("<Double-1>", self.play_selected)

        self.scrollbar = ttk.Scrollbar(self.middle_frame, orient="vertical", command=self.playlist_box.yview)
        self.scrollbar.pack(side="right", fill="y")
        self.playlist_box.config(yscrollcommand=self.scrollbar.set)

        # Bottom Frame: Controls
        self.bottom_frame = ttk.Frame(self)
        self.bottom_frame.pack(fill="x", padx=10, pady=10)

        self.controls_inner = ttk.Frame(self.bottom_frame)
        self.controls_inner.pack()

        ttk.Button(self.controls_inner, text="⏮", width=5, command=self.prev_song).pack(side="left", padx=2)
        self.play_btn = ttk.Button(self.controls_inner, text="▶", width=5, command=self.toggle_play)
        self.play_btn.pack(side="left", padx=2)
        ttk.Button(self.controls_inner, text="⏹", width=5, command=self.stop_song).pack(side="left", padx=2)
        ttk.Button(self.controls_inner, text="⏭", width=5, command=self.next_song).pack(side="left", padx=2)

        # Settings Frame
        self.settings_frame = ttk.Frame(self.bottom_frame)
        self.settings_frame.pack(pady=10)

        ttk.Label(self.settings_frame, text="Volume:").pack(side="left", padx=5)
        self.volume_slider = ttk.Scale(self.settings_frame, from_=0, to=1, orient="horizontal", command=self.engine.set_volume, length=100)
        self.volume_slider.set(0.5)
        self.volume_slider.pack(side="left", padx=5)

        self.shuffle_btn = ttk.Button(self.settings_frame, text="Shuffle: OFF", command=self.toggle_shuffle)
        self.shuffle_btn.pack(side="left", padx=5)

        self.repeat_btn = ttk.Button(self.settings_frame, text="Repeat: NONE", command=self.toggle_repeat)
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
        if self.engine.is_stopped:
            if self.engine.playlist: self.engine.play(self.engine.current_index if self.engine.current_index != -1 else 0)
        elif self.engine.current_index == -1 and self.engine.playlist: self.engine.play(0)
        else: self.engine.pause_resume()
        self.update_ui_state()

    def stop_song(self):
        self.engine.stop()
        self.update_ui_state()

    def next_song(self):
        if not self.engine.playlist: return
        should_play = not self.engine.is_paused and not self.engine.is_stopped
        self.engine.next_song()
        if should_play: self.engine.play()
        self.update_ui_state()

    def prev_song(self):
        if not self.engine.playlist: return
        should_play = not self.engine.is_paused and not self.engine.is_stopped
        self.engine.prev_song()
        if should_play: self.engine.play()
        self.update_ui_state()

    def toggle_shuffle(self):
        is_on = self.engine.toggle_shuffle()
        self.shuffle_btn.config(text=f"Shuffle: {'ON' if is_on else 'OFF'}")

    def toggle_repeat(self):
        modes = ["NONE", "ONE", "ALL"]
        current = modes.index(self.engine.repeat_mode)
        next_mode = modes[(current + 1) % len(modes)]
        self.engine.repeat_mode = next_mode
        self.repeat_btn.config(text=f"Repeat: {next_mode}")

    def on_seek_drag(self, val): self.is_dragging = True
    def on_seek_release(self, event):
        if self.engine.current_index != -1:
            total = self.engine.get_song_length()
            target_time = (self.progress_var.get() / 100) * total
            self.engine.play(start_pos=target_time)
        self.is_dragging = False

    def format_time(self, seconds):
        mins, secs = divmod(int(seconds), 60)
        return f"{mins:02d}:{secs:02d}"

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
                if total_len > 0: self.progress_var.set((current_pos / total_len) * 100)
                else: self.progress_var.set(0)
            self.time_label.config(text=f"{self.format_time(current_pos)} / {self.format_time(total_len)}")
            if not pygame.mixer.music.get_busy() and not self.engine.is_paused and not self.engine.is_stopped:
                if self.engine.repeat_mode == "ONE": self.engine.play(self.engine.current_index)
                elif self.engine.repeat_mode == "ALL" or self.engine.current_index < len(self.engine.playlist) - 1:
                    self.next_song(); self.engine.play(); self.update_ui_state()
                else: self.engine.stop(); self.update_ui_state()
        self.after(500, self.update_loop)

if __name__ == "__main__":
    app = MusicPlayerUI(MusicEngine())
    app.mainloop()
