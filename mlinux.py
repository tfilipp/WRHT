import cv2
import mediapipe as mp
import numpy as np
import pyautogui
import math
import time
import tkinter as tk
from tkinter import ttk
from typing import Tuple
import Xlib.display
import cairo
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk

class MouseMover:
    def __init__(self):
        self.display = Xlib.display.Display()
        self.screen = self.display.screen()
        self.root = self.screen.root
        self.smoothing = 0.5
        self.speed = 2.0

    def get_cursor_pos(self):
        data = self.root.query_pointer()._data
        return data["root_x"], data["root_y"]

    def move_cursor(self, x: int, y: int):
        self.root.warp_pointer(x, y)
        self.display.sync()

    def update(self, target_x: int, target_y: int):
        curr_x, curr_y = self.get_cursor_pos()
        dx = (target_x - curr_x) * self.speed
        dy = (target_y - curr_y) * self.speed
        new_x = int(curr_x + dx * self.smoothing)
        new_y = int(curr_y + dy * self.smoothing)
        self.move_cursor(new_x, new_y)

class CameraSelector:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Выбор камеры")
        self.selected_camera = None
        self.root.configure(bg='#2b2b2b')
        style = ttk.Style()
        style.theme_use('clam')
        self.cameras = self.list_cameras()
        
        label = tk.Label(self.root, text="Выберите камеру:", bg='#2b2b2b', fg='white', font=('Arial', 12))
        label.pack(pady=10)
        
        self.combo = ttk.Combobox(self.root, values=list(self.cameras.values()), width=30, font=('Arial', 10))
        self.combo.set("Выберите камеру")
        self.combo.pack(padx=20, pady=10)
        
        ttk.Button(self.root, text="Подтвердить", command=self.on_select).pack(pady=10)
        self.root.eval('tk::PlaceWindow . center')

    def list_cameras(self):
        cameras = {}
        index = 0
        while True:
            cap = cv2.VideoCapture(index)
            if not cap.read()[0]:
                break
            else:
                cameras[index] = f"Камера {index}"
                cap.release()
            index += 1
        return cameras

    def on_select(self):
        for key, value in self.cameras.items():
            if value == self.combo.get():
                self.selected_camera = key
                break
        self.root.quit()
        self.root.destroy()

    def get_camera(self):
        self.root.mainloop()
        return self.selected_camera

class CursorWindow:
    def __init__(self):
        self.window = Gtk.Window(type=Gtk.WindowType.POPUP)
        self.window.set_app_paintable(True)
        self.window.set_visual(self.window.get_screen().get_rgba_visual())
        self.window.set_keep_above(True)
        
        screen = Gdk.Screen.get_default()
        self.window.resize(16, 16)
        
        self.window.connect('draw', self.draw)
        self.window.show_all()
        
    def draw(self, widget, context):
        context.set_source_rgba(0, 0, 0, 0)
        context.set_operator(cairo.OPERATOR_SOURCE)
        context.paint()
        
        context.set_source_rgb(1, 1, 1)
        context.arc(8, 8, 7, 0, 2 * math.pi)
        context.fill()
        
    def move(self, x, y):
        self.window.move(int(x-8), int(y-8))
        
    def destroy(self):
        self.window.destroy()

class HandTracking:
    def __init__(self, camera_index=0):
        self.mp_hands = mp.solutions.hands
        self.hands = self.mp_hands.Hands(
            max_num_hands=1,
            min_detection_confidence=0.7,
            min_tracking_confidence=0.7)
        self.mp_draw = mp.solutions.drawing_utils
        
        self.cap = cv2.VideoCapture(camera_index)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
        self.cap.set(cv2.CAP_PROP_FPS, 60)
        
        self.screen_width, self.screen_height = pyautogui.size()
        self.FRAME_REDUCTION = 150
        self.SMOOTHING = 0.9
        self.CLICK_THRESHOLD = 0.02
        self.CLICK_COOLDOWN = 0.3
        self.window_size = 8
        self.averaging_window = []
        self.prev_x = self.screen_width / 2
        self.prev_y = self.screen_height / 2
        
        self.mouse_mover = MouseMover()
        self.cursor_window = CursorWindow()
        self.auto_calibrate_camera()
        pyautogui.FAILSAFE = False

    # Остальные методы остаются без изменений
    # ...

    def cleanup(self):
        self.cap.release()
        cv2.destroyAllWindows()
        self.cursor_window.destroy()

def main():
    selector = CameraSelector()
    camera_index = selector.get_camera()
    
    if camera_index is not None:
        tracker = HandTracking(camera_index)
        tracker.run()
    else:
        print("Камера не выбрана")

if __name__ == "__main__":
    main()