import sys
import subprocess
import os
import re
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QLabel, QLineEdit, QPushButton, QTextEdit, QComboBox, QCheckBox,
    QHBoxLayout, QStackedWidget, QListWidget, QFileDialog, QProgressBar, QMessageBox
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal

class DownloadThread(QThread):
    progress_signal = pyqtSignal(int)
    log_signal = pyqtSignal(str)
    finished_signal = pyqtSignal(bool)  # Changed to emit success status
    
    def __init__(self, command):
        super().__init__()
        self.command = command
        self.process = None
    
    def run(self):
        self.process = subprocess.Popen(self.command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        
        for line in iter(self.process.stdout.readline, ''):
            self.log_signal.emit(line.strip())
            match = re.search(r"(\d+\.\d+)%", line)
            if match:
                progress = float(match.group(1))
                self.progress_signal.emit(int(progress))
        
        self.process.wait()
        success = self.process.returncode == 0
        self.finished_signal.emit(success)  # Emit success status
    
    def stop(self):
        if self.process:
            self.process.terminate()

class YTDLPGUI(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()
        self.download_history = []  # List to store download history

    def init_ui(self):
        self.setWindowTitle("YouTube Downloader")
        self.setGeometry(100, 100, 800, 600)
        
        main_layout = QHBoxLayout()
        
        self.sidebar = QListWidget()
        self.sidebar.addItems(["Download Video", "Download Playlist", "Download History"])
        self.sidebar.currentRowChanged.connect(self.display_page)
        main_layout.addWidget(self.sidebar, 1)
        
        self.pages = QStackedWidget()
        
        self.download_page = self.create_download_page()
        self.pages.addWidget(self.download_page)
        
        self.playlist_page = self.create_playlist_page()
        self.pages.addWidget(self.playlist_page)
        
        self.history_page = self.create_history_page()  # New history page
        self.pages.addWidget(self.history_page)
        
        main_layout.addWidget(self.pages, 4)
        self.setLayout(main_layout)
        self.output_folder = ""
        self.download_thread = None
        self.set_dark_mode()
    
    def create_download_page(self):
        page = QWidget()
        layout = QVBoxLayout()
        
        self.url_label = QLabel("Enter YouTube URL:")
        layout.addWidget(self.url_label)
        
        self.url_input = QLineEdit()
        layout.addWidget(self.url_input)
        
        self.format_selector = QComboBox()
        self.format_selector.addItems(["Video", "Audio"])
        layout.addWidget(self.format_selector)
        
        self.quality_selector = QComboBox()
        self.quality_selector.addItems(["144p", "240p", "360p", "480p", "720p", "1080p", "Best"])
        layout.addWidget(self.quality_selector)
        
        self.subtitles_checkbox = QCheckBox("Download Subtitles")
        layout.addWidget(self.subtitles_checkbox)

        self.embed_thumbnail_checkbox = QCheckBox("Embed Thumbnail")
        layout.addWidget(self.embed_thumbnail_checkbox)

        self.file_format_label = QLabel("Select File Format:")
        layout.addWidget(self.file_format_label)

        self.file_format_selector = QComboBox()
        self.file_format_selector.addItems(["mp4", "mkv", "webm", "flv", "avi"])
        layout.addWidget(self.file_format_selector)

       
        self.output_button = QPushButton("Choose Folder")
        self.output_button.clicked.connect(self.choose_output_folder)
        layout.addWidget(self.output_button)
        
        self.custom_name_input = QLineEdit()
        self.custom_name_input.setPlaceholderText("Custom output name (optional)")
        layout.addWidget(self.custom_name_input)
        
        self.download_button = QPushButton("Download")
        self.download_button.clicked.connect(self.download_video)
        layout.addWidget(self.download_button)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)
        
        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        layout.addWidget(self.log_output)
        
        page.setLayout(layout)
        return page
    
    def create_playlist_page(self):
        page = QWidget()
        layout = QVBoxLayout()
        
        self.playlist_label = QLabel("Enter Playlist URL:")
        layout.addWidget(self.playlist_label)
        
        self.playlist_input = QLineEdit()
        layout.addWidget(self.playlist_input)
        
        self.output_button_playlist = QPushButton("Choose Folder")
        self.output_button_playlist.clicked.connect(self.choose_output_folder)
        layout.addWidget(self.output_button_playlist)
        
        self.download_playlist_button = QPushButton("Download Playlist")
        self.download_playlist_button.clicked.connect(self.download_playlist)
        layout.addWidget(self.download_playlist_button)
        
        self.log_output_playlist = QTextEdit()
        self.log_output_playlist.setReadOnly(True)
        layout.addWidget(self.log_output_playlist)
        
        page.setLayout(layout)
        return page

    def create_history_page(self):
        page = QWidget()
        layout = QVBoxLayout()
        
        self.history_output = QTextEdit()
        self.history_output.setReadOnly(True)
        layout.addWidget(self.history_output)
        
        page.setLayout(layout)
        return page
    
    def display_page(self, index):
        self.pages.setCurrentIndex(index)
        if index == 2:  # If history page is selected, update the history log
            self.update_history_log()
    
    def set_dark_mode(self):
        self.setStyleSheet("""
            background-color: #2E2E2E; color: white;
            QPushButton { background-color: #444; border-radius: 5px; padding: 5px; }
            QComboBox, QLineEdit, QTextEdit { background-color: #555; color: white; border: 1px solid #777; }
            QProgressBar { background-color: #444; color: white; border: 1px solid #777; }
            QProgressBar::chunk { background-color: #00b300; }
        """)
    
    def choose_output_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Output Folder")
        if folder:
            self.output_folder = folder
    
    def download_video(self):
        self.start_download(self.url_input.text().strip(), self.log_output)
    
    def download_playlist(self):
        self.start_download(self.playlist_input.text().strip(), self.log_output_playlist, True)
    
    def start_download(self, url, log_output, is_playlist=False):
        if not url:
            log_output.append("Error: Please enter a valid URL.")
            return
        
        if not self.output_folder:
            log_output.append("Error: Please select an output folder.")
            return
        
        yt_dlp_path = "yt-dlp"
        
        # Get the selected file format from the combo box
        file_format = self.file_format_selector.currentText()
        
        options = ["-4", "-o", f"{self.output_folder}/%(title)s.%(ext)s", "-f", file_format]
        
        if self.custom_name_input.text().strip():
            options[-2] = f"{self.output_folder}/{self.custom_name_input.text().strip()}.%(ext)s"
        
        if is_playlist:
            options.append("--yes-playlist")
        
        # Check if the "Embed Thumbnail" checkbox is selected and add the option
        if self.embed_thumbnail_checkbox.isChecked():
            options.append("--embed-thumbnail")
        
        command = [yt_dlp_path, url] + options
        
        self.download_thread = DownloadThread(command)
        self.download_thread.log_signal.connect(log_output.append)
        self.download_thread.finished_signal.connect(self.on_download_finished)
        self.download_thread.start()
        
    def on_download_finished(self, success):
        if success:
            self.log_output.append("Download complete!")
            self.download_history.append(self.url_input.text().strip())
            self.update_history_log()
        else:
            self.log_output.append("Error: Download failed. Please try again.")
            QMessageBox.critical(self, "Download Error", "The download failed. Please check the URL and try again.")
    
    def update_history_log(self):
        self.history_output.clear()
        if self.download_history:
            self.history_output.append("Download History:")
            for item in self.download_history:
                self.history_output.append(item)
        else:
            self.history_output.append("No downloads yet.")
    
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = YTDLPGUI()
    window.show()
    sys.exit(app.exec())
