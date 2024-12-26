import cv2
import mediapipe as mp
import numpy as np
import time
import math
from evdev import UInput, ecodes as e

class MouseMover:
    def __init__(self):
        self.ui = UInput()
        
    def move(self, dx, dy):
        self.ui.write(e.EV_REL, e.REL_X, dx)
        self.ui.write(e.EV_REL, e.REL_Y, dy)
        self.ui.syn()
        
    def click(self):
        self.ui.write(e.EV_KEY, e.BTN_LEFT, 1)
        self.ui.write(e.EV_KEY, e.BTN_LEFT, 0)
        self.ui.syn()

class HandTracking:
    def __init__(self, camera_index=0):
        self.mp_hands = mp.solutions.hands
        self.hands = self.mp_hands.Hands(
            max_num_hands=1,
            min_detection_confidence=0.7,
            min_tracking_confidence=0.7)
        self.mp_draw = mp.solutions.drawing_utils
        
        self.cap = cv2.VideoCapture(camera_index)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        
        self.CLICK_THRESHOLD = 0.02
        self.CLICK_COOLDOWN = 0.3
        self.SMOOTHING = 0.5
        self.SPEED = 2.0
        
        self.mouse_mover = MouseMover()
        self.prev_x, self.prev_y = 0, 0

    def process_hand(self, frame, hand_landmarks):
        middle_finger = hand_landmarks.landmark[self.mp_hands.HandLandmark.MIDDLE_FINGER_TIP]
        wrist = hand_landmarks.landmark[self.mp_hands.HandLandmark.WRIST]
        
        cursor_x = int(middle_finger.x * frame.shape[1])
        cursor_y = int(middle_finger.y * frame.shape[0])
        
        dx = int((cursor_x - self.prev_x) * self.SPEED)
        dy = int((cursor_y - self.prev_y) * self.SPEED)
        
        smoothed_dx = int(dx * self.SMOOTHING)
        smoothed_dy = int(dy * self.SMOOTHING)
        
        self.mouse_mover.move(smoothed_dx, smoothed_dy)
        
        self.prev_x, self.prev_y = cursor_x, cursor_y
        return cursor_x, cursor_y

    def calculate_distance(self, p1, p2):
        return math.sqrt((p1.x - p2.x)**2 + (p1.y - p2.y)**2)

    def cleanup(self):
        self.cap.release()
        cv2.destroyAllWindows()

    def run(self):
        last_click_time = 0
        print("\n[+] Управление:")
        print("- Перемещение курсора: движение среднего пальца")
        print("- Клик: соединить большой и указательный пальцы")
        print("- Выход: нажмите 'q'\n")
        
        while True:
            success, frame = self.cap.read()
            if not success:
                continue
                
            frame = cv2.flip(frame, 1)
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = self.hands.process(rgb_frame)
            
            if results.multi_hand_landmarks:
                for hand_landmarks in results.multi_hand_landmarks:
                    self.mp_draw.draw_landmarks(frame, hand_landmarks, self.mp_hands.HAND_CONNECTIONS)
                    
                    cursor_x, cursor_y = self.process_hand(frame, hand_landmarks)
                    
                    current_time = time.time()
                    thumb = hand_landmarks.landmark[self.mp_hands.HandLandmark.THUMB_TIP]
                    index = hand_landmarks.landmark[self.mp_hands.HandLandmark.INDEX_FINGER_TIP]
                    distance = self.calculate_distance(thumb, index)
                    
                    is_clicking = distance < self.CLICK_THRESHOLD
                    if is_clicking and current_time - last_click_time > self.CLICK_COOLDOWN:
                        self.mouse_mover.click()
                        last_click_time = current_time
            
            cv2.imshow("Hand Tracking", frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
                
        self.cleanup()

def main():
    tracker = HandTracking()
    tracker.run()

if __name__ == "__main__":
    main()