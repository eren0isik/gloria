import sys, json, os
import threading
import time
from PySide6 import QtWidgets
import pymem

# Import the feature main functions
from utils.wh import ESPWindow
from utils.fovchanger import fovchanger_main
from utils.antiflash import antiflash_main
from utils.bhop import bunnny_main
from utils.aimbot import aimbot_main
from utils.triggerbot import triggerbot_main

# Import the new CheatMenu
from cheat_menu import CheatMenu

# Global variable to hold current settings, updated by the GUI
current_settings = {}

def update_global_settings(new_settings):
    global current_settings
    current_settings = new_settings
    print("Settings updated by GUI:", current_settings) # For debugging

def start_features(stop_event, settings):
    """Starts all the background features in separate threads."""
    # Aimbot
    if settings.get('aim_active'):
        aimbot_thread = threading.Thread(target=aimbot_main, args=(settings, stop_event), daemon=True)
        aimbot_thread.start()
        print("Aimbot thread started.")

    # Trigger Bot
    if settings.get('trigger_bot_active'):
        triggerbot_thread = threading.Thread(target=triggerbot_main, args=(settings, stop_event), daemon=True)
        triggerbot_thread.start()
        print("Trigger Bot thread started.")

    # FOV Changer
    fov_thread = threading.Thread(target=fovchanger_main, args=(settings['fov'], stop_event), daemon=True)
    fov_thread.start()
    print("FOV Changer thread started.")

    # Anti-Flash
    antiflash_thread = threading.Thread(target=antiflash_main, daemon=True)
    antiflash_thread.start()
    print("Anti-Flash thread started.")

    # Bunny Hop
    bhop_thread = threading.Thread(target=bunnny_main, args=(stop_event,), daemon=True)
    bhop_thread.start()
    print("Bunny Hop thread started.")


def start_application():
    app = QtWidgets.QApplication(sys.argv)

    print("cs2.exe bekleniyor...")
    while True:
        try:
            pymem.Pymem("cs2.exe")
            break
        except pymem.exception.ProcessNotFound:
            time.sleep(1)
            continue

    print("CS2 bulundu, özellikler başlatılıyor...")

    # Initialize the CheatMenu
    menu = CheatMenu()
    
    # Get initial settings from the menu
    global current_settings
    current_settings = menu.settings

    # Connect the settings_updated signal to update global settings
    menu.settings_updated.connect(update_global_settings)

    stop_event = threading.Event()
    app.aboutToQuit.connect(stop_event.set)

    # Start features with initial settings
    start_features(stop_event, current_settings)

    # Start ESPWindow with initial settings (will be modified in utils/wh.py)
    print("ESP başlatılıyor...")
    esp_window = ESPWindow(current_settings) # Pass settings to ESPWindow
    esp_window.show()

    # Show the CheatMenu
    menu.show()

    sys.exit(app.exec())

if __name__ == "__main__":
    start_application()