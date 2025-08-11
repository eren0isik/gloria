import tkinter as tk
from tkinter import ttk
from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QCheckBox, QSlider, QPushButton, QGroupBox, QLineEdit
from PySide6.QtCore import Qt, Signal, QPoint
from PySide6.QtGui import QFont, QColor, QPalette, QPainter

import json
import os

# Config file path
CONFIG_FILE = "config.json" # This will be in the project root

class ToggleSwitch(QCheckBox):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(50, 25)
        self.setCursor(Qt.PointingHandCursor)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(Qt.NoPen)

        if self.isChecked():
            painter.setBrush(QColor("#4CAF50")) # Green
            painter.drawRoundedRect(0, 0, self.width(), self.height(), self.height() / 2, self.height() / 2)
            painter.setBrush(QColor("#FFFFFF")) # White circle
            painter.drawEllipse(self.width() - self.height() + 3, 3, self.height() - 6, self.height() - 6)
        else:
            painter.setBrush(QColor("#E0E0E0")) # Grey
            painter.drawRoundedRect(0, 0, self.width(), self.height(), self.height() / 2, self.height() / 2)
            painter.setBrush(QColor("#FFFFFF")) # White circle
            painter.drawEllipse(3, 3, self.height() - 6, self.height() - 6)

class CheatMenu(QWidget):
    settings_updated = Signal(dict) # Signal to emit when settings change

    def __init__(self):
        super().__init__()
        self.settings = self.load_settings()
        self.init_ui()
        self.apply_stylesheet()

    def load_settings(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r") as f:
                    loaded_settings = json.load(f)
                    # Merge loaded settings with defaults to ensure all keys are present
                    default_settings = self.get_default_settings()
                    default_settings.update(loaded_settings)
                    return default_settings
            except json.JSONDecodeError:
                print("Error decoding config.json. Using default settings.")
                return self.get_default_settings()
        return self.get_default_settings()

    def save_settings(self):
        with open(CONFIG_FILE, "w") as f:
            json.dump(self.settings, f, indent=4)
        self.settings_updated.emit(self.settings) # Emit signal after saving

    def get_default_settings(self):
        # Combined default settings from main.py's get_settings() and wh.py's DEFAULT_SETTINGS
        return {
            "esp_rendering": 1,
            "esp_mode": 1,
            "line_rendering": 1,
            "hp_bar_rendering": 1,
            "head_hitbox_rendering": 1,
            "bons": 1,
            "nickname": 1,
            "radius": 5000, # Aimbot radius
            "keyboard": "alt", # Aimbot hotkey
            "aim_active": 1,
            "aim_mode": 1,
            "aim_mode_distance": 1,
            "aim_smoothing": 0.0,
            "trigger_bot_active": 1,
            "keyboards": "alt", # Triggerbot hotkey (note: 'keyboards' in main.py, 'keyboard' in aimbot.py)
            "trigger_delay_ms": 10,
            "weapon": 1, # ESP weapon display
            "bomb_esp": 1,
            "fov": 110 # FOV Changer
        }

    def init_ui(self):
        self.setWindowTitle("VectrisDevHack - Cheat Menu")
        self.setGeometry(100, 100, 900, 650) # Increased size for horizontal layout and more space
        self.setWindowFlags(Qt.FramelessWindowHint) # For custom title bar

        self.main_layout = QVBoxLayout()
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        # Custom Title Bar
        self.title_bar = QWidget()
        self.title_bar.setFixedHeight(40)
        self.title_bar.setStyleSheet("""
            background-color: #2C3E50;
            color: white;
            border-bottom: 2px solid #34495E;
            border-top-left-radius: 10px; /* Rounded corners for the window */
            border-top-right-radius: 10px;
        """)
        self.title_bar_layout = QHBoxLayout(self.title_bar)
        self.title_bar_layout.setContentsMargins(10, 0, 10, 0)
        self.title_bar_layout.setSpacing(0)

        self.title_label = QLabel("VectrisDevHack")
        self.title_label.setFont(QFont("Arial", 12, QFont.Bold))
        self.title_bar_layout.addWidget(self.title_label)
        self.title_bar_layout.addStretch()

        self.minimize_button = QPushButton("-")
        self.minimize_button.setFixedSize(30, 30)
        self.minimize_button.setStyleSheet("""
            QPushButton {
                background-color: #34495E;
                color: white;
                border: none;
                border-radius: 5px;
                font-size: 16px;
            }
            QPushButton:hover {
                background-color: #5D6D7E;
            }
        """)
        self.minimize_button.clicked.connect(self.showMinimized)
        self.title_bar_layout.addWidget(self.minimize_button)

        self.close_button = QPushButton("X")
        self.close_button.setFixedSize(30, 30)
        self.close_button.setStyleSheet("""
            QPushButton {
                background-color: #E74C3C;
                color: white;
                border: none;
                border-radius: 5px;
                font-size: 16px;
            }
            QPushButton:hover {
                background-color: #C0392B;
            }
        """)
        self.close_button.clicked.connect(self.close)
        self.title_bar_layout.addWidget(self.close_button)

        self.main_layout.addWidget(self.title_bar)

        # Content Area (Horizontal Layout)
        self.content_layout = QHBoxLayout()
        self.content_layout.setContentsMargins(20, 20, 20, 20) # Increased margins
        self.content_layout.setSpacing(30) # Increased spacing between groups

        # ESP Group
        self.esp_group = self.create_group_box("ESP Settings")
        esp_layout = QVBoxLayout()
        esp_layout.addWidget(self.create_toggle_setting("ESP Rendering", "esp_rendering"))
        esp_layout.addWidget(self.create_toggle_setting("ESP Mode (Team/All)", "esp_mode"))
        esp_layout.addWidget(self.create_toggle_setting("Line Rendering", "line_rendering"))
        esp_layout.addWidget(self.create_toggle_setting("HP Bar Rendering", "hp_bar_rendering"))
        esp_layout.addWidget(self.create_toggle_setting("Head Hitbox Rendering", "head_hitbox_rendering"))
        esp_layout.addWidget(self.create_toggle_setting("Bones Rendering", "bons"))
        esp_layout.addWidget(self.create_toggle_setting("Nickname", "nickname"))
        esp_layout.addWidget(self.create_toggle_setting("Weapon", "weapon"))
        esp_layout.addWidget(self.create_toggle_setting("Bomb ESP", "bomb_esp"))
        self.esp_group.setLayout(esp_layout)
        self.content_layout.addWidget(self.esp_group)

        # Aimbot Group
        self.aimbot_group = self.create_group_box("Aimbot Settings")
        aimbot_layout = QVBoxLayout()
        aimbot_layout.addWidget(self.create_toggle_setting("Aimbot Active", "aim_active"))
        aimbot_layout.addWidget(self.create_toggle_setting("Aim Mode (1/2)", "aim_mode"))
        aimbot_layout.addWidget(self.create_toggle_setting("Aim Mode Distance (1/2)", "aim_mode_distance"))
        aimbot_layout.addWidget(self.create_slider_setting("Aim Smoothing", "aim_smoothing", 0, 100, 1.0))
        aimbot_layout.addWidget(self.create_slider_setting("Aimbot Radius", "radius", 1, 1000, 1.0))
        aimbot_layout.addWidget(self.create_text_setting("Aimbot Hotkey", "keyboard"))
        self.aimbot_group.setLayout(aimbot_layout)
        self.content_layout.addWidget(self.aimbot_group)

        # Triggerbot & FOV Group
        self.misc_group = self.create_group_box("Misc Settings")
        misc_layout = QVBoxLayout()
        misc_layout.addWidget(self.create_toggle_setting("Triggerbot Active", "trigger_bot_active"))
        misc_layout.addWidget(self.create_text_setting("Triggerbot Hotkey", "keyboards"))
        misc_layout.addWidget(self.create_slider_setting("Trigger Delay (ms)", "trigger_delay_ms", 0, 200, 1.0))
        misc_layout.addWidget(self.create_slider_setting("FOV Changer", "fov", 70, 120, 1.0))
        self.misc_group.setLayout(misc_layout)
        self.content_layout.addWidget(self.misc_group)

        self.main_layout.addLayout(self.content_layout)
        self.main_layout.addStretch() # Push content to top

        self.setLayout(self.main_layout)

    def create_group_box(self, title):
        group_box = QGroupBox(title)
        group_box.setFont(QFont("Arial", 10, QFont.Bold))
        group_box.setStyleSheet("""
            QGroupBox {
                border: 2px solid #34495E;
                border-radius: 8px;
                margin-top: 10px;
                background-color: #2C3E50;
                padding-top: 20px; /* Space for title */
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top center;
                padding: 0 10px;
                background-color: #34495E;
                color: white;
                border-radius: 5px;
            }
        """)
        return group_box

    def create_toggle_setting(self, label_text, setting_key):
        h_layout = QHBoxLayout()
        label = QLabel(label_text)
        label.setFont(QFont("Arial", 9))
        label.setStyleSheet("color: white;")
        h_layout.addWidget(label)
        h_layout.addStretch()
        toggle = ToggleSwitch()
        toggle.setChecked(bool(self.settings.get(setting_key, 0)))
        toggle.toggled.connect(lambda checked: self.update_setting(setting_key, int(checked)))
        h_layout.addWidget(toggle)
        return self.wrap_in_widget(h_layout)

    def create_slider_setting(self, label_text, setting_key, min_val, max_val, step):
        h_layout = QHBoxLayout()
        label = QLabel(label_text)
        label.setFont(QFont("Arial", 9))
        label.setStyleSheet("color: white;")
        h_layout.addWidget(label)

        slider = QSlider(Qt.Horizontal)
        slider.setRange(min_val, max_val)
        slider.setSingleStep(int(step))
        slider.setValue(int(self.settings.get(setting_key, min_val)))
        slider.setStyleSheet("""
            QSlider::groove:horizontal {
                border: 1px solid #3A506B;
                height: 8px;
                background: #5D6D7E;
                margin: 2px 0;
                border-radius: 4px;
            }
            QSlider::handle:horizontal {
                background: #4CAF50;
                border: 1px solid #3A506B;
                width: 18px;
                margin: -5px 0;
                border-radius: 9px;
            }
        """)
        slider.valueChanged.connect(lambda value: self.update_setting(setting_key, float(value)))
        h_layout.addWidget(slider)

        value_label = QLabel(str(self.settings.get(setting_key, min_val)))
        value_label.setFont(QFont("Arial", 9))
        value_label.setStyleSheet("color: white;")
        slider.valueChanged.connect(lambda value: value_label.setText(str(value)))
        h_layout.addWidget(value_label)
        return self.wrap_in_widget(h_layout)

    def create_text_setting(self, label_text, setting_key):
        h_layout = QHBoxLayout()
        label = QLabel(label_text)
        label.setFont(QFont("Arial", 9))
        label.setStyleSheet("color: white;")
        h_layout.addWidget(label)
        h_layout.addStretch()
        line_edit = QLineEdit(str(self.settings.get(setting_key, "")))
        line_edit.setStyleSheet("""
            QLineEdit {
                background-color: #34495E;
                border: 1px solid #5D6D7E;
                border-radius: 5px;
                color: white;
                padding: 5px;
            }
        """)
        line_edit.setFixedWidth(100)
        line_edit.textChanged.connect(lambda text: self.update_setting(setting_key, text))
        h_layout.addWidget(line_edit)
        return self.wrap_in_widget(h_layout)

    def wrap_in_widget(self, layout):
        widget = QWidget()
        widget.setLayout(layout)
        return widget

    def update_setting(self, key, value):
        self.settings[key] = value
        self.save_settings()

    def apply_stylesheet(self):
        self.setStyleSheet("""
            QWidget {
                background-color: #34495E;
                color: white;
                font-family: 'Segoe UI', Arial, sans-serif; /* Modern font */
                border-radius: 10px; /* Rounded corners for the main window */
            }
            QLabel {
                color: white;
            }
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 8px 15px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #45A049;
            }
            QGroupBox {
                border: 2px solid #34495E;
                border-radius: 8px;
                margin-top: 10px;
                background-color: #2C3E50;
                padding-top: 20px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top center;
                padding: 0 10px;
                background-color: #34495E;
                color: white;
                border-radius: 5px;
            }
        """)
        palette = self.palette()
        palette.setColor(QPalette.Window, QColor("#34495E"))
        palette.setColor(QPalette.WindowText, QColor("white"))
        self.setPalette(palette)

    # Custom title bar drag functionality
    _drag_position = QPoint() # Initialize outside methods

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and self.title_bar.underMouse():
            self._drag_position = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton and self.title_bar.underMouse():
            self.move(event.globalPos() - self._drag_position)
            event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    menu = CheatMenu()
    menu.show()
    sys.exit(app.exec())
