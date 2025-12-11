import os
import sys
import subprocess
import shutil
from PyQt5 import QtCore, QtGui, QtWidgets

# --- UTILS ---

def _app_base_dir():
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

def _find_ffmpeg_binary():
    base_dir = _app_base_dir()
    exe_name = "ffmpeg.exe" if os.name == "nt" else "ffmpeg"
    local_path = os.path.join(base_dir, exe_name)
    if os.path.isfile(local_path):
        return local_path
    path_ffmpeg = shutil.which("ffmpeg")
    if path_ffmpeg:
        return path_ffmpeg
    return None

def _install_ffmpeg_windows(parent, installer_path):
    # This relies on an external batch file 'ffmpeginstall.bat'
    if parent is not None:
        reply = QtWidgets.QMessageBox.question(
            parent,
            "FFmpeg not found",
            "FFmpeg is not installed or not in PATH.\n\n"
            "Do you want to run the included installer now?\n"
            "(Requires Windows 10/11, internet, and winget.)",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
        )
        if reply != QtWidgets.QMessageBox.Yes:
            return False
    try:
        creationflags = getattr(subprocess, "CREATE_NEW_CONSOLE", 0)
        subprocess.call(
            ["cmd", "/c", installer_path],
            creationflags=creationflags,
        )
        return True
    except Exception:
        if parent is not None:
            QtWidgets.QMessageBox.critical(
                parent,
                "Installer error",
                "Could not run ffmpeg installer.\n"
                "Please install ffmpeg manually and try again.",
            )
        return False

def _install_ffmpeg_macos(parent):
    brew_path = shutil.which("brew")
    if not brew_path:
        if parent is not None:
            QtWidgets.QMessageBox.critical(
                parent,
                "Homebrew not found",
                "FFmpeg is missing and Homebrew (brew) is not installed.\n\n"
                "On macOS, please install Homebrew first from:\n"
                "https://brew.sh\n\n"
                "Then run in Terminal:\n"
                "  brew install ffmpeg",
            )
        return False

    if parent is not None:
        reply = QtWidgets.QMessageBox.question(
            parent,
            "Install FFmpeg",
            "FFmpeg is not installed.\n\n"
            "Do you want to run:\n"
            "  brew install ffmpeg\n"
            "This may take a few minutes.",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
        )
        if reply != QtWidgets.QMessageBox.Yes:
            return False

    try:
        subprocess.call([brew_path, "install", "ffmpeg"])
        return True
    except Exception:
        if parent is not None:
            QtWidgets.QMessageBox.critical(
                parent,
                "Install error",
                "Could not run 'brew install ffmpeg'.\n"
                "Install FFmpeg Manually And try",
            )
        return False

def ensure_ffmpeg(parent=None):
    ff = _find_ffmpeg_binary()
    if ff:
        return ff

    # WINDOWS
    if sys.platform.startswith("win"):
        installer = os.path.join(_app_base_dir(), "ffmpeginstall.bat")
        # Only try automatic install if the bat file exists
        if os.path.isfile(installer):
            ok = _install_ffmpeg_windows(parent, installer)
            if ok:
                ff = _find_ffmpeg_binary()
                if ff:
                    return ff
        
        # Fallback message
        if parent is not None:
            QtWidgets.QMessageBox.critical(
                parent,
                "FFmpeg Missing",
                "FFmpeg is required but cannot be found.\n"
                "Please install it manually (download from ffmpeg.org or use 'winget install ffmpeg')\n"
                "and ensure 'ffmpeg' is in your system PATH.",
            )
        return None

    # macOS
    if sys.platform == "darwin":
        ok = _install_ffmpeg_macos(parent)
        if ok:
            ff = _find_ffmpeg_binary()
            if ff:
                return ff
        if parent is not None:
            QtWidgets.QMessageBox.critical(
                parent,
                "FFmpeg not available",
                "FFmpeg is required.\nRun 'brew install ffmpeg' in Terminal.",
            )
        return None

    # Linux/Other
    if parent is not None:
        QtWidgets.QMessageBox.critical(
            parent,
            "FFmpeg not available",
            "FFmpeg is required.\nPlease install ffmpeg (e.g. sudo apt install ffmpeg).",
        )
    return None

# --- WORKER ---

class FfmpegWorker(QtCore.QObject):
    log_signal = QtCore.pyqtSignal(str)
    finished = QtCore.pyqtSignal(bool)

    def __init__(self, command, workdir):
        super().__init__()
        self.command = command
        self.workdir = workdir

    @QtCore.pyqtSlot()
    def run(self):
        try:
            startupinfo = None
            creationflags = 0

            if os.name == "nt":
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                creationflags = subprocess.CREATE_NO_WINDOW

            process = subprocess.Popen(
                self.command,
                cwd=self.workdir,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                startupinfo=startupinfo,
                creationflags=creationflags,
            )
        except FileNotFoundError:
            self.log_signal.emit("ERROR: ffmpeg execution failed. Check installation.\n")
            self.finished.emit(False)
            return

        for line in process.stdout:
            self.log_signal.emit(line)

        process.wait()
        self.finished.emit(process.returncode == 0)

# --- GUI COMPONENTS ---

class RetroButton(QtWidgets.QPushButton):
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))
        self.setMinimumHeight(36)
        self.setStyleSheet("""
            QPushButton {
                color: #0ff;
                background-color: rgba(10, 10, 25, 0.9);
                border: 2px solid #0ff;
                border-radius: 8px;
                font-size: 13px;
                font-weight: 600;
                padding: 4px 10px;
            }
            QPushButton:hover {
                background-color: rgba(0, 255, 255, 0.18);
                border-color: #6ff;
            }
            QPushButton:pressed {
                background-color: #044;
                border-color: #0aa;
            }
            QPushButton:disabled {
                color: #555;
                border-color: #333;
                background-color: rgba(8, 8, 18, 0.7);
            }
        """)

class RetroWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Gehans Audio Converter")
        self.setMinimumSize(960, 560)
        self.input_path = ""
        self.output_dir = os.path.expanduser("~")
        self._setup_ui()
        self._apply_style()
        self.worker_thread = None

    def _setup_ui(self):
        central = QtWidgets.QWidget()
        self.setCentralWidget(central)
        root_layout = QtWidgets.QVBoxLayout(central)
        root_layout.setContentsMargins(16, 16, 16, 16)
        root_layout.setSpacing(12)

        # Header
        header = QtWidgets.QHBoxLayout()
        self.title_label = QtWidgets.QLabel("AUDIO CONVERTER")
        self.title_label.setObjectName("titleLabel")
        self.big_label = QtWidgets.QLabel("No files Converted")
        self.big_label.setObjectName("bigLabel")
        header.addWidget(self.title_label)
        header.addStretch(1)
        header.addWidget(self.big_label)
        root_layout.addLayout(header)

        main_layout = QtWidgets.QHBoxLayout()
        main_layout.setSpacing(14)
        root_layout.addLayout(main_layout, 1)

        # Left Panel
        left_panel = QtWidgets.QFrame()
        left_panel.setObjectName("leftPanel")
        left_layout = QtWidgets.QVBoxLayout(left_panel)
        left_layout.setContentsMargins(14, 14, 14, 14)
        left_layout.setSpacing(10)

        self.sub_label = QtWidgets.QLabel("Pick a file. Pick a format. Convert it using ffmpeg.")
        self.sub_label.setObjectName("subLabel")
        self.sub_label.setWordWrap(True)
        left_layout.addWidget(self.sub_label)

        # Input
        file_row = QtWidgets.QHBoxLayout()
        file_label = QtWidgets.QLabel("INPUT")
        file_label.setObjectName("miniLabel")
        self.file_display = QtWidgets.QLineEdit()
        self.file_display.setPlaceholderText("Select A file Human")
        self.file_display.setReadOnly(True)
        browse_btn = QtWidgets.QPushButton("BROWSE")
        browse_btn.clicked.connect(self.pick_file)
        file_row.addWidget(file_label)
        file_row.addWidget(self.file_display, 1)
        file_row.addWidget(browse_btn)
        left_layout.addLayout(file_row)

        # Output
        out_row = QtWidgets.QHBoxLayout()
        out_label = QtWidgets.QLabel("OUTPUT DIR")
        out_label.setObjectName("miniLabel")
        self.output_display = QtWidgets.QLineEdit(self.output_dir)
        self.output_display.setReadOnly(True)
        out_btn = QtWidgets.QPushButton("CHANGE")
        out_btn.clicked.connect(self.pick_output_folder)
        out_row.addWidget(out_label)
        out_row.addWidget(self.output_display, 1)
        out_row.addWidget(out_btn)
        left_layout.addLayout(out_row)

        # Format & Quality
        form_row = QtWidgets.QHBoxLayout()
        fmt_label = QtWidgets.QLabel("FORMAT")
        fmt_label.setObjectName("miniLabel")
        self.format_combo = QtWidgets.QComboBox()
        self.format_combo.addItems(["mp3", "opus", "wav", "flac", "m4a", "aac", "ogg", "wma"])
        self.format_combo.setCurrentText("mp3")

        vibe_label = QtWidgets.QLabel("QUALITY")
        vibe_label.setObjectName("miniLabel")
        self.quality_combo = QtWidgets.QComboBox()
        self.quality_combo.addItems(["High quality", "Balanced", "Smaller file"])
        self.quality_combo.setCurrentText("Balanced")

        form_row.addWidget(fmt_label)
        form_row.addWidget(self.format_combo, 1)
        form_row.addWidget(vibe_label)
        form_row.addWidget(self.quality_combo, 1)
        left_layout.addLayout(form_row)

        # Options
        self.normalize_box = QtWidgets.QCheckBox("Normalize loudness")
        self.normalize_box.setChecked(True)
        self.strip_subs_box = QtWidgets.QCheckBox("Strip subtitles (if they exist)")
        self.strip_subs_box.setChecked(False)
        left_layout.addWidget(self.normalize_box)
        left_layout.addWidget(self.strip_subs_box)

        left_layout.addStretch(1)

        # Action Buttons
        btn_row = QtWidgets.QHBoxLayout()
        self.convert_button = RetroButton("CONVERT")
        self.convert_button.clicked.connect(self.start_convert)
        self.cancel_button = RetroButton("CANCEL")
        self.cancel_button.setEnabled(True)
        self.cancel_button.clicked.connect(self.cancel_convert)
        btn_row.addStretch(1)
        btn_row.addWidget(self.convert_button)
        btn_row.addWidget(self.cancel_button)
        left_layout.addLayout(btn_row)

        # Right Panel (Log)
        right_panel = QtWidgets.QFrame()
        right_panel.setObjectName("rightPanel")
        right_layout = QtWidgets.QVBoxLayout(right_panel)
        right_layout.setContentsMargins(14, 14, 14, 14)
        right_layout.setSpacing(8)

        log_title = QtWidgets.QLabel("LOG")
        log_title.setObjectName("miniLabel")
        right_layout.addWidget(log_title)
        self.log_view = QtWidgets.QPlainTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setObjectName("logView")
        right_layout.addWidget(self.log_view, 1)

        main_layout.addWidget(left_panel, 3)
        main_layout.addWidget(right_panel, 4)

    def _apply_style(self):
        self.setStyleSheet("""
            QMainWindow { background-color: #050712; }
            #leftPanel { background-color: #0c1024; border-radius: 10px; }
            #rightPanel { background-color: #070a18; border-radius: 10px; }
            #titleLabel { color: #00f5ff; font-size: 20px; font-weight: 800; letter-spacing: 2px; }
            #bigLabel { color: #ff00ff; font-size: 26px; font-weight: 900; }
            #subLabel { color: #a9b3df; font-size: 12px; }
            #miniLabel { color: #c2c8f0; font-size: 11px; letter-spacing: 1px; }
            QLineEdit { background-color: #050714; border: 1px solid #24294a; border-radius: 6px; color: #ffffff; padding: 4px 6px; }
            QComboBox { background-color: #050714; border: 1px solid #24294a; border-radius: 6px; color: #ffffff; padding: 2px 4px; }
            QComboBox QAbstractItemView { background-color: #050714; color: #ffffff; selection-background-color: #00f5ff; }
            QCheckBox { color: #b8c0e0; font-size: 12px; }
            QCheckBox::indicator { width: 16px; height: 16px; }
            QCheckBox::indicator:unchecked { border: 1px solid #00f5ff; background-color: #050712; }
            QCheckBox::indicator:checked { border: 1px solid #00f5ff; background-color: #00f5ff; }
            QPlainTextEdit#logView { background-color: #050714; border: 1px solid #24294a; border-radius: 6px; color: #e3e7ff; font-family: Consolas, monospace; font-size: 11px; }
            QScrollBar:vertical { background: #050712; width: 10px; margin: 0px; }
            QScrollBar::handle:vertical { background: #2b2f4a; min-height: 20px; border-radius: 4px; }
        """)

    def append_log(self, text):
        self.log_view.appendPlainText(text)
        self.log_view.verticalScrollBar().setValue(
            self.log_view.verticalScrollBar().maximum()
        )

    def set_busy(self, busy: bool):
        self.convert_button.setEnabled(not busy)
        self.cancel_button.setEnabled(busy)
        if busy:
            self.sub_label.setText("Converting... don’t close this or i will come to your house.")
        else:
            self.sub_label.setText("Pick a file. Pick a format. Convert it with ffmpeg.")

    def pick_file(self):
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "Select Input Media", "",
            "Media Files (*.mp4 *.mkv *.webm *.mp3 *.wav *.flac *.mov *.avi *.m4a *.opus *.ogg *.wma);;All Files (*.*)"
        )
        if path:
            self.input_path = path
            self.file_display.setText(path)
            self.append_log(f"INPUT: {path}\n")

    def pick_output_folder(self):
        folder = QtWidgets.QFileDialog.getExistingDirectory(self, "Select Output Folder", self.output_dir)
        if folder:
            self.output_dir = folder
            self.output_display.setText(folder)
            self.append_log(f"OUTPUT DIR: {folder}\n")

    def start_convert(self):
        if not self.input_path:
            QtWidgets.QMessageBox.warning(self, "No input", "Pick a file first.")
            return

        if not os.path.isdir(self.output_dir):
            QtWidgets.QMessageBox.warning(self, "Invalid output", "Output folder does not exist.")
            return

        ffmpeg_path = ensure_ffmpeg(self)
        if not ffmpeg_path:
            return

        in_path = self.input_path
        base_name = os.path.splitext(os.path.basename(in_path))[0]
        ext = self.format_combo.currentText()
        out_path = os.path.join(self.output_dir, f"{base_name}.{ext}")
        quality = self.quality_combo.currentText()

        # Build FFmpeg Command
        cmd = [ffmpeg_path, "-y", "-i", in_path]

        # Audio Codec Logic
        # -vn removes video stream (ensures we get audio file)
        cmd.append("-vn")

        if ext == "mp3":
            cmd += ["-c:a", "libmp3lame"]
            if quality == "High quality":
                cmd += ["-b:a", "320k"]
            elif quality == "Smaller file":
                cmd += ["-b:a", "128k"]
            else:
                cmd += ["-b:a", "192k"]

        elif ext == "opus":
            cmd += ["-c:a", "libopus"]
            if quality == "High quality":
                 cmd += ["-b:a", "160k"]
            elif quality == "Smaller file":
                 cmd += ["-b:a", "64k"]
            else:
                 cmd += ["-b:a", "128k"]

        elif ext == "wav":
            cmd += ["-c:a", "pcm_s16le"]

        elif ext == "flac":
            cmd += ["-c:a", "flac"]

        elif ext in ["m4a", "aac"]:
            cmd += ["-c:a", "aac"]
            if quality == "High quality":
                cmd += ["-b:a", "256k"]
            else:
                cmd += ["-b:a", "192k"]

        elif ext == "ogg":
            cmd += ["-c:a", "libvorbis"]
            if quality == "High quality":
                 cmd += ["-q:a", "6"]
            else:
                 cmd += ["-q:a", "4"]

        elif ext == "wma":
            cmd += ["-c:a", "wmav2", "-b:a", "192k"]

        # Filters
        if self.normalize_box.isChecked():
            cmd += ["-af", "loudnorm"]
        
        # Note: -sn strips subtitles, but usually -vn implicitly handles that for audio formats
        if self.strip_subs_box.isChecked():
            cmd += ["-sn"]

        cmd.append(out_path)

        self.append_log("=== Starting conversion ===\n")
        self.append_log(f"CMD: {' '.join(cmd)}\n")
        
        self.set_busy(True)
        self.worker_thread = QtCore.QThread()
        self.worker = FfmpegWorker(cmd, self.output_dir)
        self.worker.moveToThread(self.worker_thread)
        self.worker_thread.started.connect(self.worker.run)
        self.worker.log_signal.connect(self.append_log)
        self.worker.finished.connect(self.on_convert_finished)
        self.worker.finished.connect(self.worker_thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.worker_thread.finished.connect(self.worker_thread.deleteLater)
        self.worker_thread.start()

    def cancel_convert(self):
        QtWidgets.QMessageBox.information(
            self, "Cancel", "To cancel, close the application window."
        )

    def on_convert_finished(self, ok: bool):
        self.set_busy(False)
        if ok:
            self.append_log("\n=== Conversion finished successfully ===\n")
            self.sub_label.setText("File converted. You’re one step closer to audio supremacy.")
            try:
                current = int(self.big_label.text())
                self.big_label.setText(str(current + 1))
            except ValueError:
                self.big_label.setText("1")
        else:
            self.append_log("\n=== Conversion NOT WORKING BHAI ===\n")
            self.sub_label.setText("Conversion NOT WORKING BHAI. Check the log for details.")

def main():
    app = QtWidgets.QApplication(sys.argv)
    app.setApplicationName("Gehans Audio Converter")
    QtCore.QCoreApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling, True)
    win = RetroWindow()
    win.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()