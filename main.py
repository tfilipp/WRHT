import cv2
import mediapipe as mp
import numpy as np
import pyautogui
import math
import time
import tkinter as tk
from tkinter import ttk
import win32gui
import win32con
import win32api
import keyboard
from PIL import Image, ImageTk
import pygame
from ctypes import windll, Structure, c_long, byref, POINTER
from typing import Tuple
from win32gui import GetCursorInfo

def move_cursor(x: int, y: int):
    win32api.SetCursorPos((x, y))

class POINT(Structure):
    _fields_ = [("x", c_long), ("y", c_long)]

def get_cursor_pos() -> Tuple[int, int]:
    pt = POINT()
    windll.user32.GetCursorPos(byref(pt))
    return (pt.x, pt.y)

class MouseMover:
    def __init__(self):
        self.last_pos = get_cursor_pos()
        self.smoothing = 0.5
        self.speed = 2.0
        
    def update(self, target_x: int, target_y: int):
        curr_x, curr_y = get_cursor_pos()
        dx = (target_x - curr_x) * self.speed
        dy = (target_y - curr_y) * self.speed
        new_x = int(curr_x + dx * self.smoothing)
        new_y = int(curr_y + dy * self.smoothing)
        move_cursor(new_x, new_y)
        self.last_pos = (new_x, new_y)

class ControlPanel:
    def __init__(self, root):
        self.window = tk.Toplevel()
        self.window.title("Control Panel")
        self.window.geometry("300x400")
        self.window.overrideredirect(True)
        self.window.attributes('-topmost', True, '-alpha', 0.9)
        self.window.configure(bg='#1e1e1e')
        
        self.header = tk.Label(self.window, 
                             text="Панель управления",
                             fg='white',
                             bg='#1e1e1e',
                             font=('Arial', 12, 'bold'))
        self.header.pack(pady=10)
        
        buttons = [
            ("🔊 Громкость +", "volumeup"),
            ("🔉 Громкость -", "volumedown"),
            ("🔇 Без звука", "volumemute"),
            ("⏯️ Пауза/Воспр.", "playpause"),
            ("⏭️ Следующий", "nexttrack"),
            ("⏮️ Предыдущий", "prevtrack"),
            ("🖥️ Рабочий стол", "windows+d"),
            ("🔍 Поиск", "windows+s")
        ]
        
        for text, command in buttons:
            btn = tk.Button(self.window,
                          text=text,
                          command=lambda cmd=command: self.execute_command(cmd),
                          bg='#2d2d2d',
                          fg='white',
                          relief='flat',
                          font=('Arial', 10),
                          width=20,
                          height=2)
            btn.pack(pady=5, padx=20)
            btn.bind('<Enter>', lambda e, b=btn: b.configure(bg='#3d3d3d'))
            btn.bind('<Leave>', lambda e, b=btn: b.configure(bg='#2d2d2d'))
        
        self.close_btn = tk.Button(self.window,
                                 text="✖ Закрыть",
                                 command=self.hide,
                                 bg='#ff4444',
                                 fg='white',
                                 relief='flat',
                                 font=('Arial', 10))
        self.close_btn.pack(pady=10)
        
        self.window.withdraw()

    def show(self, x, y):
        print("[DEBUG] Showing panel at", x, y)
        self.window.deiconify()
        self.window.geometry(f"+{x}+{y}")
        self.window.update()
        
    def hide(self):
        print("[DEBUG] Hiding panel")
        self.window.withdraw()
        
    def execute_command(self, command):
        print(f"[DEBUG] Executing command: {command}")
        try:
            keyboard.press_and_release(command)
        except Exception as e:
            print(f"[ERROR] Failed to execute command: {e}")

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
                try:
                    backend_name = cap.getBackendName()
                    camera_name = f"Камера {index} ({backend_name})"
                except:
                    camera_name = f"Камера {index}"
                cameras[index] = camera_name
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

class HandTracking:
    def __init__(self, camera_index=0):
        self.mp_hands = mp.solutions.hands
        self.hands = self.mp_hands.Hands(
            max_num_hands=1,
            min_detection_confidence=0.7,
            min_tracking_confidence=0.7)
        self.mp_draw = mp.solutions.drawing_utils
        
        self.cap = cv2.VideoCapture(camera_index, cv2.CAP_DSHOW)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
        self.cap.set(cv2.CAP_PROP_FPS, 60)
        self.cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc('M','J','P','G'))
        
        self.screen_width, self.screen_height = pyautogui.size()
        self.cursor_radius = 8
        self.FRAME_REDUCTION = 150
        self.SMOOTHING = 0.9
        self.CLICK_THRESHOLD = 0.02
        self.CLICK_COOLDOWN = 0.3
        self.window_size = 8
        self.averaging_window = []
        self.prev_x = self.screen_width / 2
        self.prev_y = self.screen_height / 2

        self.root = tk.Tk()
        self.root.withdraw()
        self.control_panel = ControlPanel(self.root)
        self.panel_visible = False
        
        self.hand_positions = []
        self.last_panel_toggle = 0
        self.panel_cooldown = 1.0
        self.min_wave_distance = 200
        self.max_positions = 10
        
        self.mouse_mover = MouseMover()
        self.create_cursor_window()
        self.auto_calibrate_camera()
        pyautogui.FAILSAFE = False

    def auto_calibrate_camera(self):
        print("[+] Калибровка камеры...")
        brightness_values = []
        
        for _ in range(30):
            success, frame = self.cap.read()
            if success:
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                brightness_values.append(np.mean(gray))
                
        if brightness_values:
            avg_brightness = np.mean(brightness_values)
            
            if avg_brightness < 100:
                self.cap.set(cv2.CAP_PROP_BRIGHTNESS, 150)
                self.cap.set(cv2.CAP_PROP_CONTRAST, 150)
                self.CLICK_THRESHOLD = 0.025
            elif avg_brightness > 200:
                self.cap.set(cv2.CAP_PROP_BRIGHTNESS, 50)
                self.cap.set(cv2.CAP_PROP_CONTRAST, 50)
                self.CLICK_THRESHOLD = 0.015
                
        print("[+] Калибровка завершена")

    def create_cursor_window(self):
        self.cursor_window = win32gui.CreateWindowEx(
            win32con.WS_EX_LAYERED | win32con.WS_EX_TRANSPARENT | win32con.WS_EX_TOPMOST,
            'static', None, win32con.WS_POPUP,
            0, 0, self.cursor_radius*2, self.cursor_radius*2,
            None, None, None, None)
            
        win32gui.SetLayeredWindowAttributes(
            self.cursor_window, win32api.RGB(0,0,0), 0, win32con.LWA_COLORKEY)
            
        win32gui.ShowWindow(self.cursor_window, win32con.SW_SHOW)

    def update_cursor(self, x, y, is_clicking=False):
        hdc = win32gui.GetDC(self.cursor_window)
        win32gui.MoveWindow(self.cursor_window,
                           int(x-self.cursor_radius),
                           int(y-self.cursor_radius),
                           self.cursor_radius*2,
                           self.cursor_radius*2,
                           True)
                           
        mem_dc = win32gui.CreateCompatibleDC(hdc)
        bitmap = win32gui.CreateCompatibleBitmap(hdc, self.cursor_radius*2, self.cursor_radius*2)
        win32gui.SelectObject(mem_dc, bitmap)
        
        outer_brush = win32gui.CreateSolidBrush(win32api.RGB(0,0,0))
        win32gui.SelectObject(mem_dc, outer_brush)
        win32gui.Ellipse(mem_dc, 0, 0, self.cursor_radius*2, self.cursor_radius*2)
        
        inner_brush = win32gui.CreateSolidBrush(win32api.RGB(255,255,255))
        win32gui.SelectObject(mem_dc, inner_brush)
        padding = 2
        win32gui.Ellipse(mem_dc, padding, padding,
                        self.cursor_radius*2-padding,
                        self.cursor_radius*2-padding)
                        
        if is_clicking:
            click_brush = win32gui.CreateSolidBrush(win32api.RGB(255,0,0))
            win32gui.SelectObject(mem_dc, click_brush)
            win32gui.Ellipse(mem_dc, padding*2, padding*2,
                            self.cursor_radius*2-padding*2,
                            self.cursor_radius*2-padding*2)
                            
        win32gui.BitBlt(hdc, 0, 0, self.cursor_radius*2, self.cursor_radius*2,
                       mem_dc, 0, 0, win32con.SRCCOPY)
                       
        win32gui.DeleteObject(bitmap)
        win32gui.DeleteDC(mem_dc)
        win32gui.ReleaseDC(self.cursor_window, hdc)

    def check_wave(self, hand_landmarks, frame_width):
        index_mcp = hand_landmarks.landmark[self.mp_hands.HandLandmark.INDEX_FINGER_MCP]
        middle_mcp = hand_landmarks.landmark[self.mp_hands.HandLandmark.MIDDLE_FINGER_MCP]
        
        palm_x = int((index_mcp.x + middle_mcp.x) / 2 * frame_width)
        
        self.hand_positions.append(palm_x)
        
        if len(self.hand_positions) > self.max_positions:
            self.hand_positions.pop(0)
            
        if len(self.hand_positions) >= 5:
            min_x = min(self.hand_positions)
            max_x = max(self.hand_positions)
            distance = max_x - min_x
            
            current_time = time.time()
            if distance > self.min_wave_distance and current_time - self.last_panel_toggle > self.panel_cooldown:
                self.last_panel_toggle = current_time
                self.hand_positions = []
                return True
                
        return False

    def process_hand(self, frame, hand_landmarks):
        middle_finger = hand_landmarks.landmark[self.mp_hands.HandLandmark.MIDDLE_FINGER_TIP]
        wrist = hand_landmarks.landmark[self.mp_hands.HandLandmark.WRIST]
        mcp = hand_landmarks.landmark[self.mp_hands.HandLandmark.MIDDLE_FINGER_MCP]
        
        palm_center_x = (wrist.x + mcp.x) / 2
        palm_center_y = (wrist.y + mcp.y) / 2
        
        normalized_x = (middle_finger.x - palm_center_x) * 2 + palm_center_x
        normalized_y = (middle_finger.y - palm_center_y) * 2 + palm_center_y
        
        cursor_x = np.interp(normalized_x,
                           [self.FRAME_REDUCTION/frame.shape[1], 1-self.FRAME_REDUCTION/frame.shape[1]],
                           [0, self.screen_width])
        cursor_y = np.interp(normalized_y,
                           [self.FRAME_REDUCTION/frame.shape[0], 1-self.FRAME_REDUCTION/frame.shape[0]],
                           [0, self.screen_height])
        
        self.averaging_window.append((cursor_x, cursor_y))
        if len(self.averaging_window) > self.window_size:
            self.averaging_window.pop(0)
            
        avg_x = sum(x for x, _ in self.averaging_window) / len(self.averaging_window)
        avg_y = sum(y for _, y in self.averaging_window) / len(self.averaging_window)
        
        smoothed_x = int(self.SMOOTHING * self.prev_x + (1 - self.SMOOTHING) * avg_x)
        smoothed_y = int(self.SMOOTHING * self.prev_y + (1 - self.SMOOTHING) * avg_y)
        
        self.mouse_mover.update(smoothed_x, smoothed_y)
        return smoothed_x, smoothed_y

    def calculate_distance(self, p1, p2):
        return math.sqrt((p1.x - p2.x)**2 + (p1.y - p2.y)**2)

    def cleanup(self):
        self.cap.release()
        cv2.destroyAllWindows()
        win32gui.DestroyWindow(self.cursor_window)
        self.root.destroy()

    def run(self):
        last_click_time = 0
        print("\n[+] Управление:")
        print("- Перемещение курсора: движение среднего пальца")
        print("- Клик: соединить большой и указательный пальцы") 
        print("- Панель управления: быстрое движение рукой влево-вправо")
        print("- Выход: нажмите 'q'\n")
        
        while True:
            success, frame = self.cap.read()
            if not success:
                continue
                
            frame = cv2.flip(frame, 1)
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = self.hands.process(rgb_frame)
            
            if self.hand_positions:
                for i in range(1, len(self.hand_positions)):
                    cv2.line(frame, 
                            (self.hand_positions[i-1], int(frame.shape[0]/2)),
                            (self.hand_positions[i], int(frame.shape[0]/2)),
                            (0, 255, 0), 2)
            
            if results.multi_hand_landmarks:
                for hand_landmarks in results.multi_hand_landmarks:
                    self.mp_draw.draw_landmarks(frame, hand_landmarks, self.mp_hands.HAND_CONNECTIONS)
                    
                    cursor_x, cursor_y = self.process_hand(frame, hand_landmarks)
                    self.prev_x, self.prev_y = cursor_x, cursor_y
                    
                    if self.check_wave(hand_landmarks, frame.shape[1]):
                        print("[DEBUG] Wave detected!")
                        if not self.panel_visible:
                            self.panel_visible = True
                            self.control_panel.show(int(cursor_x) + 50, int(cursor_y))
                            print(f"[DEBUG] Showing panel at {cursor_x}, {cursor_y}")
                        else:
                            self.panel_visible = False
                            self.control_panel.hide()
                            print("[DEBUG] Panel hidden")
                    
                    current_time = time.time()
                    thumb = hand_landmarks.landmark[self.mp_hands.HandLandmark.THUMB_TIP]
                    index = hand_landmarks.landmark[self.mp_hands.HandLandmark.INDEX_FINGER_TIP]
                    distance = self.calculate_distance(thumb, index)
                    
                    self.is_clicking = distance < self.CLICK_THRESHOLD
                    if self.is_clicking and current_time - last_click_time > self.CLICK_COOLDOWN:
                        if not self.panel_visible:
                            pyautogui.click()
                        last_click_time = current_time
                    
                    self.update_cursor(cursor_x, cursor_y, self.is_clicking)
            else:
                self.hand_positions = []
            
            cv2.putText(frame, f"Panel: {'Open' if self.panel_visible else 'Closed'}", 
                       (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            
            if len(self.hand_positions) > 0:
                cv2.putText(frame, "Movement detected", 
                           (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 165, 0), 2)
            
            cv2.imshow("Hand Tracking", frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
                
        self.cleanup()

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