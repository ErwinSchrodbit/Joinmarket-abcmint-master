import sys
import os

# --- Monkey Patch for --noconsole mode ---
# JoinMarket expects sys.stdout to have .isatty(), but in --noconsole mode it is None.
if sys.stdout is None:
    class DummyStream:
        def write(self, text): pass
        def flush(self): pass
        def isatty(self): return False
    sys.stdout = DummyStream()
    sys.stderr = DummyStream()
# -----------------------------------------

import json
import threading
import webbrowser
import time
import socket
import urllib.request
import base64
from functools import partial

# Adjust paths before importing anything else
if getattr(sys, 'frozen', False):
    # If running as a bundled EXE
    BASE_DIR = sys._MEIPASS
else:
    # If running as a script
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Add internal paths to sys.path to ensure imports work
sys.path.insert(0, BASE_DIR)
sys.path.insert(0, os.path.join(BASE_DIR, 'service'))
sys.path.insert(0, os.path.join(BASE_DIR, 'joinmarket-clientserver-master', 'src'))

try:
    from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                                 QLabel, QLineEdit, QPushButton, QMessageBox, 
                                 QSystemTrayIcon, QMenu, QTextEdit, QFrame, QHBoxLayout)
    from PyQt6.QtCore import Qt, QThread, pyqtSignal, QObject, QTimer
    from PyQt6.QtGui import QIcon, QFont, QColor, QPalette, QAction, QPixmap, QPainter
except ImportError as e:
    print(f"PyQt6 Error Details: {e}")
    # Allow running without PyQt for headless testing if needed, but here we exit
    sys.exit(1) 

# Try to import service modules
try:
    from waitress import serve
    from service.app import app as flask_app
except ImportError as e:
    import traceback
    print(f"CRITICAL ERROR: Service dependencies missing.\nDetail: {e}")
    print(traceback.format_exc())
    input("Press Enter to exit...")
    sys.exit(1)


def get_app_data_dir():
    """Get the application data directory in AppData/Local"""
    app_data = os.getenv('LOCALAPPDATA')
    if not app_data:
        app_data = os.path.expanduser('~')
    
    data_dir = os.path.join(app_data, 'JoinMarket-ABCMint')
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
    return data_dir

CONFIG_FILE = os.path.join(get_app_data_dir(), 'launcher_config.json')

class MatrixPalette(QPalette):
    def __init__(self):
        super().__init__()
        self.setColor(QPalette.ColorRole.Window, QColor(0, 0, 0))
        self.setColor(QPalette.ColorRole.WindowText, QColor(0, 255, 65))  # Matrix Green
        self.setColor(QPalette.ColorRole.Base, QColor(10, 10, 10))
        self.setColor(QPalette.ColorRole.AlternateBase, QColor(0, 20, 0))
        self.setColor(QPalette.ColorRole.ToolTipBase, QColor(0, 0, 0))
        self.setColor(QPalette.ColorRole.ToolTipText, QColor(0, 255, 65))
        self.setColor(QPalette.ColorRole.Text, QColor(0, 255, 65))
        self.setColor(QPalette.ColorRole.Button, QColor(0, 20, 0))
        self.setColor(QPalette.ColorRole.ButtonText, QColor(0, 255, 65))
        self.setColor(QPalette.ColorRole.BrightText, Qt.GlobalColor.red)
        self.setColor(QPalette.ColorRole.Link, QColor(42, 130, 218))
        self.setColor(QPalette.ColorRole.Highlight, QColor(0, 255, 65))
        self.setColor(QPalette.ColorRole.HighlightedText, QColor(0, 0, 0))

class ServiceThread(QThread):
    log_signal = pyqtSignal(str)
    finished_signal = pyqtSignal()

    def __init__(self, host, port):
        super().__init__()
        self.host = host
        self.port = port
        self._is_running = True

    def run(self):
        # Display 127.0.0.1 to the user for clarity, even if we bind to 0.0.0.0
        display_host = "127.0.0.1" if self.host == "0.0.0.0" else self.host
        self.log_signal.emit(f"[*] Initializing ABCMint Service on {display_host}:{self.port}...")
        try:
            # Waitress serve is blocking, so this thread stays alive
            serve(flask_app, host=self.host, port=self.port, threads=4)
        except Exception as e:
            self.log_signal.emit(f"[!] Error: {str(e)}")
        self.finished_signal.emit()

    def stop(self):
        # Waitress doesn't have a clean stop method exposed easily, 
        # but killing the daemon thread or process usually works for this use case.
        self._is_running = False

class LauncherWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ABCMint Mix Launcher // V.1.0")
        self.resize(600, 500)  # Set initial size but allow resizing
        # Removed setFixedSize to allow resizing
        
        # Matrix Styling
        self.setPalette(MatrixPalette())
        self.font_main = QFont("Courier New", 10)
        self.font_bold = QFont("Courier New", 12, QFont.Weight.Bold)
        self.setFont(self.font_main)

        # Central Widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        layout.setSpacing(20) # Increase spacing between elements
        layout.setContentsMargins(40, 40, 40, 40) # Increase margins

        # Title / Header
        title_label = QLabel("ABCMint MIX_PROTOCOL_INIT")
        title_label.setFont(QFont("Courier New", 16, QFont.Weight.Bold))
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)

        # Separator
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        layout.addWidget(line)

        # Form Layout
        form_layout = QVBoxLayout()
        
        self.inputs = {}
        fields = [
            ("RPC Port", "ABCMINT_RPC_PORT", "8332"),
            ("RPC User", "ABCMINT_RPC_USER", ""),
            ("RPC Password", "ABCMINT_RPC_PASSWORD", "")
        ]

        for label_text, env_key, default in fields:
            lbl = QLabel(f"> {label_text}:")
            lbl.setFont(self.font_main) # Ensure label font is set
            inp = QLineEdit()
            inp.setPlaceholderText(default)
            inp.setFont(self.font_main) # Ensure input font is set
            inp.setMinimumHeight(30) # Make input boxes slightly taller
            inp.setStyleSheet("QLineEdit { border: 1px solid #00ff41; background-color: #000000; color: #00ff41; padding: 5px; }")
            if "PASSWORD" in env_key:
                inp.setEchoMode(QLineEdit.EchoMode.Password)
            
            self.inputs[env_key] = inp
            form_layout.addWidget(lbl)
            form_layout.addWidget(inp)
            form_layout.addSpacing(10) # Add spacing between field groups

        layout.addLayout(form_layout)

        # Buttons
        btn_layout = QHBoxLayout()
        
        self.btn_start = QPushButton("[ INITIALIZE LINK ]")
        self.btn_start.setFont(self.font_bold)
        self.btn_start.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_start.setStyleSheet("QPushButton { border: 2px solid #00ff41; padding: 10px; background-color: #001400; } QPushButton:hover { background-color: #00ff41; color: #000000; }")
        self.btn_start.clicked.connect(self.start_service)
        
        # Removed Reset Button
        # self.btn_reset = QPushButton("[ RESET CONFIG ]")
        # self.btn_reset.setCursor(Qt.CursorShape.PointingHandCursor)
        # self.btn_reset.setStyleSheet("QPushButton { border: 1px solid #008f11; padding: 10px; color: #008f11; } QPushButton:hover { border: 1px solid #00ff41; color: #00ff41; }")
        # self.btn_reset.clicked.connect(self.reset_config)

        # btn_layout.addWidget(self.btn_reset)
        btn_layout.addWidget(self.btn_start)
        layout.addLayout(btn_layout)

        # Log Area
        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        self.log_area.setFixedHeight(100)
        self.log_area.setStyleSheet("border: 1px dashed #008f11; background-color: #000000; color: #008f11; font-size: 9pt;")
        layout.addWidget(self.log_area)

        # Load Config
        self.load_config()

        # Tray Icon
        self.init_tray()
        
        self.service_thread = None

    def log(self, msg):
        self.log_area.append(f"> {msg}")
        # Auto scroll
        sb = self.log_area.verticalScrollBar()
        sb.setValue(sb.maximum())

    def init_tray(self):
        self.tray_icon = QSystemTrayIcon(self)
        
        # Create a simple green square icon if none exists
        pixmap = QPixmap(16, 16)
        pixmap.fill(QColor(0, 255, 65))
        icon = QIcon(pixmap)
        self.tray_icon.setIcon(icon)
        
        menu = QMenu()
        
        action_show = QAction("Show Interface", self)
        action_show.triggered.connect(self.show_window)
        menu.addAction(action_show)
        
        action_browser = QAction("Open Web UI", self)
        action_browser.triggered.connect(lambda: webbrowser.open("http://localhost:5000"))
        menu.addAction(action_browser)
        
        menu.addSeparator()
        
        action_exit = QAction("Terminate", self)
        action_exit.triggered.connect(self.terminate_app)
        menu.addAction(action_exit)
        
        self.tray_icon.setContextMenu(menu)
        self.tray_icon.activated.connect(self.on_tray_icon_activated)
        self.tray_icon.show()

    def on_tray_icon_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.show_window()

    def show_window(self):
        self.showNormal()
        self.activateWindow()

    def closeEvent(self, event):
        # Minimize to tray instead of closing
        if self.tray_icon.isVisible():
            self.hide()
            self.tray_icon.showMessage(
                "ABCMint Launcher",
                "Service is running in background.",
                QSystemTrayIcon.MessageIcon.Information,
                2000
            )
            event.ignore()
        else:
            event.accept()

    def terminate_app(self):
        self.tray_icon.hide()
        QApplication.quit()

    def load_config(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r') as f:
                    data = json.load(f)
                    for key, inp in self.inputs.items():
                        if key in data:
                            inp.setText(data[key])
                self.log("Configuration loaded.")
            except Exception as e:
                self.log(f"Failed to load config: {e}")

    def save_config(self):
        data = {}
        for key, inp in self.inputs.items():
            data[key] = inp.text()
        try:
            with open(CONFIG_FILE, 'w') as f:
                json.dump(data, f)
            self.log("Configuration saved.")
        except Exception as e:
            self.log(f"Failed to save config: {e}")

    def reset_config(self):
        reply = QMessageBox.question(self, 'Reset Config', 
                                     "Are you sure you want to clear all RPC settings?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, 
                                     QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            for inp in self.inputs.values():
                inp.clear()
            if os.path.exists(CONFIG_FILE):
                os.remove(CONFIG_FILE)
            self.log("Configuration reset.")

    def test_connection(self):
        # Get current values
        host = "127.0.0.1"
        port = self.inputs["ABCMINT_RPC_PORT"].text().strip() or "8332"
        user = self.inputs["ABCMINT_RPC_USER"].text().strip()
        password = self.inputs["ABCMINT_RPC_PASSWORD"].text().strip()

        url = f"http://{host}:{port}"
        payload = json.dumps({
            "jsonrpc": "1.0", 
            "id": "launcher_test", 
            "method": "getpeerinfo", 
            "params": []
        }).encode()

        req = urllib.request.Request(url, data=payload, headers={'Content-Type': 'application/json'})
        
        # Basic Auth
        auth_str = f"{user}:{password}"
        auth_bytes = auth_str.encode('ascii')
        base64_bytes = base64.b64encode(auth_bytes)
        base64_str = base64_bytes.decode('ascii')
        req.add_header("Authorization", f"Basic {base64_str}")

        try:
            with urllib.request.urlopen(req, timeout=5) as response:
                if response.status == 200:
                    return True, "Connection Successful"
                else:
                    return False, f"HTTP Status: {response.status}"
        except urllib.error.HTTPError as e:
            if e.code == 401:
                return False, "Authentication Failed (Wrong User/Pass)"
            return False, f"HTTP Error: {e.code} {e.reason}"
        except urllib.error.URLError as e:
            return False, f"Connection Failed: {e.reason}"
        except Exception as e:
            return False, f"Error: {str(e)}"

    def start_service(self):
        if self.service_thread and self.service_thread.isRunning():
            self.log("Service is already running.")
            webbrowser.open("http://localhost:5000")
            return

        # Pre-flight check
        self.log("Testing RPC Connection...")
        success, msg = self.test_connection()
        
        if not success:
            self.log(f"[!] {msg}")
            QMessageBox.critical(self, "Connection Failed", 
                f"Could not connect to ABCMint Node:\n{msg}\n\nPlease check your RPC settings.")
            return

        self.log("[+] RPC Connection Verified.")

        # Set Environment Variables
        # Always force localhost for RPC Host
        os.environ["ABCMINT_RPC_HOST"] = "127.0.0.1"
        
        for key, inp in self.inputs.items():
            val = inp.text().strip()
            if not val and "PORT" in key:
                 val = "8332" # Default
            if val:
                os.environ[key] = val
        
        # Save config before starting
        self.save_config()

        self.btn_start.setEnabled(False)
        self.btn_start.setText("[ RUNNING... ]")
        self.inputs['ABCMINT_RPC_PASSWORD'].setEnabled(False) # Lock password field

        self.service_thread = ServiceThread("0.0.0.0", 5000)
        self.service_thread.log_signal.connect(self.log)
        self.service_thread.start()

        # Wait a bit then open browser
        QTimer.singleShot(2000, lambda: webbrowser.open("http://localhost:5000"))
        QTimer.singleShot(2000, lambda: self.log("Web Interface Launched."))

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    
    # Single Instance Lock using QSharedMemory
    from PyQt6.QtCore import QSharedMemory
    
    shared_memory = QSharedMemory("JoinMarketABCMintLauncherInstance")
    
    if not shared_memory.create(1):
        # Memory segment already exists, meaning another instance is running
        QMessageBox.warning(None, "Already Running", 
                            "Another instance of ABCMint Launcher is already running.\nPlease check your system tray.")
        sys.exit(0)

    window = LauncherWindow()
    window.show()
    
    sys.exit(app.exec())