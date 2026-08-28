import base64
import io
import os
import threading
import uuid
import sounddevice as sd
import soundfile as sf
import numpy as np
from socket import socket, AF_INET, SOCK_STREAM

from customtkinter import *
from tkinter import filedialog
from PIL import Image

HOST = '2.tcp.eu.ngrok.io'
PORT = 17270


class MainWindow(CTk):

    def __init__(self):
        super().__init__()

        self.geometry('600x500')
        self.title("Chat Client")

        self.username = "new user"
        self.recording = False
        self.audio_frames = []

        self.is_show_menu = False
        self.speed_animate_menu = -20

        self.menu_frame = CTkFrame(self, width=30)
        self.menu_frame.pack_propagate(False)
        self.menu_frame.pack(side="left", fill="y")

        self.btn = CTkButton(self.menu_frame, text='▶️', command=self.toggle_show_menu, width=30)
        self.btn.pack(anchor="nw", pady=2)

        self.main_container = CTkFrame(self, fg_color="transparent")
        self.main_container.pack(side="right", fill="both", expand=True)

        self.chat_field = CTkScrollableFrame(self.main_container)
        self.chat_field.pack(side="top", fill="both", expand=True, padx=5, pady=5)

        self.bottom_frame = CTkFrame(self.main_container, fg_color="transparent")
        self.bottom_frame.pack(side="bottom", fill="x", padx=5, pady=5)

        self.message_entry = CTkEntry(self.bottom_frame, placeholder_text='Введіть повідомлення:', height=40)
        self.message_entry.pack(side="left", fill="x", expand=True, padx=(0, 5))

        self.send_button = CTkButton(self.bottom_frame, text='>', width=40, height=40, command=self.send_message)
        self.send_button.pack(side="left", padx=2)

        self.open_img_button = CTkButton(self.bottom_frame, text='📂', width=40, height=40, command=self.open_image)
        self.open_img_button.pack(side="left", padx=2)

        self.rec_button = CTkButton(self.bottom_frame, text="🎙", width=40, height=40)
        self.rec_button.pack(side="left", padx=2)
        self.rec_button.bind("<ButtonPress-1>", self.on_press)
        self.rec_button.bind("<ButtonRelease-1>", self.on_release)

        try:
            self.sock = socket(AF_INET, SOCK_STREAM)
            self.sock.connect((HOST, PORT))
            hello = f"TEXT@{self.username}@[SYSTEM] {self.username} приєднався(лась) до чату!\n"
            self.sock.send(hello.encode('utf-8'))
            threading.Thread(target=self.recv_message, daemon=True).start()
        except Exception as e:
            self.add_message(f"Не вдалося підключитися до сервера: {e}")

    def toggle_show_menu(self):

        if self.is_show_menu:
            self.is_show_menu = False
            self.speed_animate_menu *= -1
            self.btn.configure(text='▶️')
            self.show_menu()
        else:
            self.is_show_menu = True
            self.speed_animate_menu *= -1
            self.btn.configure(text='◀️')
            self.show_menu()
            self.label = CTkLabel(self.menu_frame, text='Імʼя')
            self.label.pack(pady=10)
            self.entry = CTkEntry(self.menu_frame, placeholder_text="Ваш нік...")
            self.entry.pack(pady=5)
            self.save_button = CTkButton(self.menu_frame, text="Зберегти", command=self.save_name)
            self.save_button.pack(pady=5)

    def show_menu(self):

        current_w = self.menu_frame.winfo_width()
        self.menu_frame.configure(width=current_w + self.speed_animate_menu)

        if not current_w >= 200 and self.is_show_menu:
            self.after(10, self.show_menu)
        elif current_w >= 60 and not self.is_show_menu:
            self.after(10, self.show_menu)
            if getattr(self, "label", None):
                self.label.destroy()
            if getattr(self, "entry", None):
                self.entry.destroy()
            if getattr(self, "save_button", None):
                self.save_button.destroy()

    def save_name(self):

        new_name = self.entry.get().strip()
        if new_name:
            self.username = new_name
            self.add_message(f"Ваш новий нік: {self.username}")

    def audio_callback(self, indata, frames, time_info, status):

        if self.recording:
            self.audio_frames.append(indata.copy())

    def on_press(self, event):

        if self.recording:
            return
        self.recording = True
        self.audio_frames = []
        self.rec_button.configure(fg_color="red")

        self.fs = 44100
        self.stream = sd.InputStream(samplerate=self.fs, channels=1, dtype='int16', callback=self.audio_callback)
        self.stream.start()

    def on_release(self, event):

        if not self.recording:
            return
        self.recording = False
        self.rec_button.configure(fg_color="#3B8ED0")

        try:
            self.stream.stop()
            self.stream.close()
        except Exception:
            pass

        if not self.audio_frames:
            return

        recorded_data = np.concatenate(self.audio_frames, axis=0)

        if len(recorded_data) < self.fs * 0.5:
            return

        if len(recorded_data) > 0:
            filename = f"voice_{uuid.uuid4()}.wav"
            sf.write(filename, recorded_data, self.fs)
            self.send_voice(filename)

    def play_audio(self, filepath):

        try:
            data, samplerate = sf.read(filepath, dtype='float32')
            threading.Thread(target=lambda: sd.play(data, samplerate, blocking=True), daemon=True).start()
        except Exception as e:
            self.add_message(f"Помилка відтворення: {e}")

    def add_message(self, message, img=None, custom_widget=None):

        message_frame = CTkFrame(self.chat_field, fg_color='grey')
        message_frame.pack(pady=5, anchor='w', padx=5, fill='x')

        if img is not None:
            CTkLabel(message_frame, text=message, wraplength=350,
                     text_color='white', image=img, compound='top',
                     justify='left').pack(padx=10, pady=5)
        elif custom_widget is not None:
            CTkLabel(message_frame, text=message, text_color='white', justify='left').pack(padx=10, pady=5)
            custom_widget(message_frame)
        else:
            CTkLabel(message_frame, text=message, wraplength=350,
                     text_color='white', justify='left').pack(padx=10, pady=5)

    def send_message(self):

        message = self.message_entry.get()
        if message:
            self.add_message(f"{self.username}: {message}")
            data = f"TEXT@{self.username}@{message}\n"
            try:
                self.sock.sendall(data.encode())
            except:
                pass
        self.message_entry.delete(0, END)

    def send_voice(self, filename):

        try:
            with open(filename, "rb") as f:
                raw = f.read()
            b64_data = base64.b64encode(raw).decode()

            data = f"AUDIO@{self.username}@{filename}@{b64_data}\n"
            self.sock.sendall(data.encode())

            self.add_message(
                f"Ви: надіслали голосове повідомлення 🎙",
                custom_widget=lambda parent, path=filename: CTkButton(
                    parent, text="▶️ Відтворити",
                    command=lambda p=path: self.play_audio(p)
                ).pack(padx=10, pady=5, anchor='w')
            )
        except Exception as e:
            self.add_message(f"Помилка відправки голосу: {e}")

    def recv_message(self):

        buffer = ""
        while True:
            try:
                chunk = self.sock.recv(65536)
                if not chunk:
                    break
                buffer += chunk.decode('utf-8', errors='ignore')

                while "\n" in buffer:
                    line, buffer = buffer.split("\n", 1)
                    self.after(0, self.handle_line, line.strip())

            except:
                break
        self.sock.close()

    def handle_line(self, line):

        if not line:
            return
        parts = line.split("@", 3)
        msg_type = parts[0]

        if msg_type == "TEXT":
            if len(parts) >= 3:
                author = parts[1]
                message = parts[2]
                self.add_message(f"{author}: {message}")
        elif msg_type == "IMAGE":
            if len(parts) >= 4:
                author = parts[1]
                filename = parts[2]
                b64_img = parts[3]
                try:
                    img_data = base64.b64decode(b64_img)
                    pil_img = Image.open(io.BytesIO(img_data))
                    ctk_img = CTkImage(pil_img, size=(300, 300))
                    self.add_message(f"{author} надіслав(ла) зображення: {filename}", img=ctk_img)
                except Exception as e:
                    self.add_message(f"Помилка відображення зображення: {e}")
        elif msg_type == "AUDIO":
            if len(parts) >= 4:
                author = parts[1]
                filename = parts[2]
                b64_audio = parts[3]
                try:
                    audio_data = base64.b64decode(b64_audio)
                    save_path = f"received_{filename}"

                    with open(save_path, "wb") as f:
                        f.write(audio_data)

                    self.add_message(
                        f"{author} надіслав(ла) голосове повідомлення 🎙",
                        custom_widget=lambda parent, path=save_path: CTkButton(
                            parent, text="▶️ Відтворити",
                            command=lambda p=path: self.play_audio(p)
                        ).pack(padx=10, pady=5, anchor='w')
                    )
                except Exception as e:
                    self.add_message(f"Помилка отримання голосового: {e}")
        else:
            self.add_message(line)

    def open_image(self):

        file_name = filedialog.askopenfilename()
        if not file_name:
            return
        try:
            with open(file_name, "rb") as f:
                raw = f.read()
            b64_data = base64.b64encode(raw).decode()
            short_name = os.path.basename(file_name)
            data = f"IMAGE@{self.username}@{short_name}@{b64_data}\n"
            self.sock.sendall(data.encode())
            self.add_message(f"{self.username}: {short_name}",
                             CTkImage(light_image=Image.open(file_name), size=(300, 300)))
        except Exception as e:
            self.add_message(f"Не вдалося надіслати зображення: {e}")


if __name__ == "__main__":
    win = MainWindow()
    win.mainloop()
