import tkinter as tk
from tkinter import ttk, filedialog
import pygame
import os
import random

class MusicPlayer(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Music Player")
        self.geometry("800x600")

        pygame.mixer.init()

        self.playlist = []
        self.original_playlist = []
        self.current_song_index = -1
        self.paused = False
        self.shuffle_mode = False
        self.repeat_mode = "NONE" # NONE, ONE, ALL

        self.create_widgets()
        # self.load_dummy_playlist() # For testing - REMOVED

    def create_widgets(self):
        # --- Top Frame for Song Info and Progress ---
        top_frame = ttk.Frame(self)
        top_frame.pack(pady=10, padx=10, fill="x")

        self.song_label = ttk.Label(top_frame, text="No song selected", font=("Helvetica", 12))
        self.song_label.pack()

        self.progress_bar = ttk.Progressbar(top_frame, orient="horizontal", length=400, mode="determinate")
        self.progress_bar.pack(pady=5)
        self.progress_bar.bind("<Button-1>", self.seek)
        
        self.time_label = ttk.Label(top_frame, text="00:00 / 00:00")
        self.time_label.pack()

        # --- Playlist Frame ---
        playlist_frame = ttk.Frame(self)
        playlist_frame.pack(pady=10, padx=10, fill="both", expand=True)

        self.playlist_box = tk.Listbox(playlist_frame, selectmode=tk.SINGLE, bg="black", fg="white", selectbackground="gray", selectforeground="black")
        self.playlist_box.pack(fill="both", expand=True)
        self.playlist_box.bind("<Double-1>", self.play_selected_song)

        # --- Controls Frame ---
        controls_frame = ttk.Frame(self)
        controls_frame.pack(pady=10)

        self.prev_button = ttk.Button(controls_frame, text="⏮", command=self.prev_song)
        self.prev_button.grid(row=0, column=0, padx=5)

        self.play_button = ttk.Button(controls_frame, text="▶", command=self.play_song)
        self.play_button.grid(row=0, column=1, padx=5)

        self.pause_button = ttk.Button(controls_frame, text="⏸", command=self.pause_song)
        self.pause_button.grid(row=0, column=2, padx=5)
        
        self.stop_button = ttk.Button(controls_frame, text="⏹", command=self.stop_song)
        self.stop_button.grid(row=0, column=3, padx=5)

        self.next_button = ttk.Button(controls_frame, text="⏭", command=self.next_song)
        self.next_button.grid(row=0, column=4, padx=5)
        
        # --- Volume and Mode Frame ---
        volume_mode_frame = ttk.Frame(self)
        volume_mode_frame.pack(pady=5, padx=10, fill="x")
        
        # Volume
        volume_label = ttk.Label(volume_mode_frame, text="Volume:")
        volume_label.pack(side="left", padx=5)
        self.volume_slider = ttk.Scale(volume_mode_frame, from_=0, to=1, orient="horizontal", command=self.set_volume)
        self.volume_slider.pack(side="left", fill="x", expand=True)
        self.volume_slider.set(0.5)

        # Shuffle and Repeat
        self.shuffle_button = ttk.Button(volume_mode_frame, text="Shuffle: OFF", command=self.toggle_shuffle)
        self.shuffle_button.pack(side="left", padx=5)
        self.repeat_button = ttk.Button(volume_mode_frame, text="Repeat: OFF", command=self.toggle_repeat)
        self.repeat_button.pack(side="left", padx=5)


        # --- Menu ---
        menubar = tk.Menu(self)
        self.config(menu=menubar)

        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Open Files", command=self.add_songs)
        file_menu.add_command(label="Open Folder", command=self.add_folder)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.quit)

    def add_folder(self):
        folder = filedialog.askdirectory(title="Select Folder")
        if folder:
            files_added = False
            for root, dirs, files in os.walk(folder):
                for file in files:
                    if file.endswith((".mp3", ".ogg", ".wav", ".flac")):
                        self.playlist.append(os.path.join(root, file))
                        self.original_playlist.append(os.path.join(root, file))
                        files_added = True
            
            if files_added:
                self.update_playlist_box()
                # If this is the first song added, start playing it
                if self.current_song_index == -1 and self.playlist:
                    self.current_song_index = 0
                    self.play_song()

    def add_songs(self):
        files = filedialog.askopenfilenames(
            title="Select Music Files",
            filetypes=(("Audio Files", "*.mp3 *.ogg *.wav *.flac"), ("All files", "*.*"))
        )
        
        if files:
            for file in files:
                self.playlist.append(file)
                self.original_playlist.append(file)
            self.update_playlist_box()

            # If this is the first song added, start playing it
            if self.current_song_index == -1 and self.playlist:
                self.current_song_index = 0
                self.play_song()
    
    def play_selected_song(self, event):
        if self.playlist_box.curselection():
            self.current_song_index = self.playlist_box.curselection()[0]
            self.paused = False
            self.play_song()
            
    def update_playlist_box(self):
        self.playlist_box.delete(0, tk.END)
        for song in self.playlist:
            self.playlist_box.insert(tk.END, os.path.basename(song))

    def play_song(self):
        if not self.playlist: return

        if self.current_song_index == -1:
            self.current_song_index = 0
            
        if self.paused:
            pygame.mixer.music.unpause()
            self.paused = False
        else:
            # Update selection in listbox
            self.playlist_box.select_clear(0, tk.END)
            self.playlist_box.select_set(self.current_song_index)
            self.playlist_box.activate(self.current_song_index)
            
            song_path = self.playlist[self.current_song_index]
            try:
                pygame.mixer.music.load(song_path)
                pygame.mixer.music.play()
                self.song_label.config(text=os.path.basename(song_path))
                self.update_progress()
            except pygame.error as e:
                self.song_label.config(text=f"Error: {e}")

    def update_progress(self):
        if pygame.mixer.music.get_busy() and not self.paused:
            current_time = pygame.mixer.music.get_pos() / 1000
            try:
                song_sound = pygame.mixer.Sound(self.playlist[self.current_song_index])
                song_length = song_sound.get_length()
            except (pygame.error, IndexError):
                song_length = 0

            self.progress_bar["value"] = current_time
            self.progress_bar["maximum"] = song_length
            
            self.time_label.config(text=f"{self.format_time(current_time)} / {self.format_time(song_length)}")
        
        # Auto-play next song
        if not pygame.mixer.music.get_busy() and not self.paused and self.current_song_index != -1:
            self.handle_song_end()

        self.after(1000, self.update_progress)
        
    def seek(self, event):
        if self.playlist:
            try:
                song_sound = pygame.mixer.Sound(self.playlist[self.current_song_index])
                song_length = song_sound.get_length()
                seek_time = (event.x / self.progress_bar.winfo_width()) * song_length
                pygame.mixer.music.set_pos(seek_time)
            except (pygame.error, IndexError):
                pass # Ignore seek if song is not valid


    def pause_song(self):
        if not self.paused:
            pygame.mixer.music.pause()
            self.paused = True
        else:
            pygame.mixer.music.unpause()
            self.paused = False
            self.update_progress()
            
    def stop_song(self):
        pygame.mixer.music.stop()
        self.song_label.config(text="No song selected")
        self.paused = False
        self.progress_bar["value"] = 0
        self.time_label.config(text="00:00 / 00:00")
        self.current_song_index = -1

    def next_song(self):
        if not self.playlist: return
        if self.shuffle_mode:
            self.current_song_index = random.randint(0, len(self.playlist) - 1)
        elif self.current_song_index < len(self.playlist) - 1:
            self.current_song_index += 1
        else: # End of playlist
            self.current_song_index = 0
            
        self.paused = False
        self.play_song()

    def prev_song(self):
        if not self.playlist: return
        if self.shuffle_mode:
            self.current_song_index = random.randint(0, len(self.playlist) - 1)
        elif self.current_song_index > 0:
            self.current_song_index -= 1
        else: # At the beginning of the playlist
            self.current_song_index = len(self.playlist) - 1

        self.paused = False
        self.play_song()
            
    def set_volume(self, val):
        volume = float(val)
        pygame.mixer.music.set_volume(volume)
        
    def format_time(self, seconds):
        mins, secs = divmod(seconds, 60)
        mins = round(mins)
        secs = round(secs)
        return f"{int(mins):02d}:{int(secs):02d}"

    def toggle_shuffle(self):
        if not self.playlist: return
        self.shuffle_mode = not self.shuffle_mode
        self.shuffle_button.config(text=f"Shuffle: {'ON' if self.shuffle_mode else 'OFF'}")
        
        if self.shuffle_mode:
            # When turning shuffle on, shuffle the playlist
            current_song = self.playlist[self.current_song_index]
            random.shuffle(self.playlist)
            self.current_song_index = self.playlist.index(current_song)
            self.update_playlist_box()
        else:
            # When turning shuffle off, revert to original order
            current_song = self.playlist[self.current_song_index]
            self.playlist = list(self.original_playlist)
            self.current_song_index = self.playlist.index(current_song)
            self.update_playlist_box()

    def toggle_repeat(self):
        if self.repeat_mode == "NONE":
            self.repeat_mode = "ONE"
            self.repeat_button.config(text="Repeat: ONE")
        elif self.repeat_mode == "ONE":
            self.repeat_mode = "ALL"
            self.repeat_button.config(text="Repeat: ALL")
        else:
            self.repeat_mode = "NONE"
            self.repeat_button.config(text="Repeat: OFF")

    def handle_song_end(self):
        if self.repeat_mode == "ONE":
            self.play_song() # Play the same song again
        elif self.repeat_mode == "ALL":
            self.next_song()
        elif self.shuffle_mode:
             self.next_song()
        else: # Repeat is OFF and Shuffle is OFF
            if self.current_song_index < len(self.playlist) - 1:
                self.next_song()
            else:
                # Stop playback if at the end of the playlist
                self.stop_song()


if __name__ == "__main__":
    app = MusicPlayer()
    app.mainloop()