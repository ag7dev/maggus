import ctypes
import cv2
import json
import math
import mss
import os
import sys
import time
import torch
import numpy as np
import win32api
import win32con
import win32gui
from termcolor import colored
from colorama import init, Fore, Back, Style
from ultralytics import YOLO

# Initializing colorama for cross-platform support
init(autoreset=True)

# Define necessary structures for input simulation
class MouseInput(ctypes.Structure):
    _fields_ = [("dx", ctypes.c_long),
                ("dy", ctypes.c_long),
                ("mouseData", ctypes.c_ulong),
                ("dwFlags", ctypes.c_ulong),
                ("time", ctypes.c_ulong),
                ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong))]

class Input_I(ctypes.Union):
    _fields_ = [("mi", MouseInput)]

class Input(ctypes.Structure):
    _fields_ = [("type", ctypes.c_ulong),
                ("ii", Input_I)]

# Auto Screen Resolution
screensize = {'X': ctypes.windll.user32.GetSystemMetrics(0), 'Y': ctypes.windll.user32.GetSystemMetrics(1)}

# Screen resolution settings
screen_res_x = screensize['X']
screen_res_y = screensize['Y']

# Divide screen_res by 2
screen_x = int(screen_res_x / 2)
screen_y = int(screen_res_y / 2)

aim_height = 10  # The lower the number, the higher the aim_height. For example: 2 would be the head and 100 would be the feet.

confidence = 0.45  # How confident the AI needs to be for it to lock on to the player. Default is 45%

use_trigger_bot = True  # Will shoot if crosshair is locked on the player

class Aimbot:
    extra = ctypes.c_ulong(0)
    ii_ = Input_I()
    screen = mss.mss()
    pixel_increment = 1  # Controls how many pixels the mouse moves for each relative movement
    with open("lib/config/config.json") as f:
        sens_config = json.load(f)
    aimbot_status = Fore.GREEN + "ENABLED"  # Default status
    transparent_mode = False  # Default mode is normal (not transparent)

    def __init__(self, box_constant=350, collect_data=False, mouse_delay=0.0009):
        self.box_constant = box_constant  # Controls the size of the detection box (equaling the width and height)
        
        print(Fore.CYAN + "[INFO] Loading the neural network model")
        self.model = YOLO('lib/best.pt')
        if torch.cuda.is_available():
            print(Fore.GREEN + "CUDA ACCELERATION [ENABLED]")
        else:
            print(Fore.RED + "[!] CUDA ACCELERATION IS UNAVAILABLE")
            print(Fore.RED + "[!] Check your PyTorch installation, else performance will be poor")

        self.conf = confidence  # base confidence threshold (or base detection (0-1)
        self.iou = 0.01  # NMS IoU (0-1)
        self.collect_data = collect_data
        self.mouse_delay = mouse_delay

        print(Fore.YELLOW + "\n[INFO] PRESS 'F1' TO TOGGLE AIMBOT\n[INFO] PRESS 'F2' TO QUIT\n[INFO] PRESS 'F3' TO TOGGLE TRANSPARENT MODE")

    @staticmethod
    def update_status_aimbot():
        if Aimbot.aimbot_status == Fore.GREEN + "ENABLED":
            Aimbot.aimbot_status = Fore.RED + "DISABLED"
        else:
            Aimbot.aimbot_status = Fore.GREEN + "ENABLED"
        sys.stdout.write("\033[K")
        print(f"[!] AIMBOT IS [{Aimbot.aimbot_status}]", end="\r")

    @staticmethod
    def toggle_transparent_mode():
        Aimbot.transparent_mode = not Aimbot.transparent_mode
        mode = "TRANSPARENT" if Aimbot.transparent_mode else "NORMAL"
        sys.stdout.write("\033[K")
        print(f"[!] MODE IS [{mode}]", end="\r")

    @staticmethod
    def left_click():
        ctypes.windll.user32.mouse_event(0x0002)  # Left mouse down
        Aimbot.sleep(0.0001)
        ctypes.windll.user32.mouse_event(0x0004)  # Left mouse up

    @staticmethod
    def sleep(duration, get_now=time.perf_counter):
        if duration == 0:
            return
        now = get_now()
        end = now + duration
        while now < end:
            now = get_now()

    @staticmethod
    def is_aimbot_enabled():
        return Aimbot.aimbot_status == Fore.GREEN + "ENABLED"

    @staticmethod
    def is_shooting():
        return win32api.GetKeyState(0x01) in (-127, -128)
    
    @staticmethod
    def is_targeted():
        return win32api.GetKeyState(0x02) in (-127, -128)

    @staticmethod
    def is_target_locked(x, y):
        threshold = 5  # Plus/minus 5 pixel threshold
        return screen_x - threshold <= x <= screen_x + threshold and screen_y - threshold <= y <= screen_y + threshold

    def move_crosshair(self, x, y):
        if Aimbot.is_targeted():
            scale = Aimbot.sens_config["targeting_scale"]
        else:
            return

        for rel_x, rel_y in Aimbot.interpolate_coordinates_from_center((x, y), scale):
            Aimbot.ii_.mi = MouseInput(rel_x, rel_y, 0, 0x0001, 0, ctypes.pointer(Aimbot.extra))
            input_obj = Input(ctypes.c_ulong(0), Aimbot.ii_)
            ctypes.windll.user32.SendInput(1, ctypes.byref(input_obj), ctypes.sizeof(input_obj))
            Aimbot.sleep(self.mouse_delay)

    # Generator yields pixel tuples for relative movement
    @staticmethod
    def interpolate_coordinates_from_center(absolute_coordinates, scale):
        diff_x = (absolute_coordinates[0] - screen_x) * scale / Aimbot.pixel_increment
        diff_y = (absolute_coordinates[1] - screen_y) * scale / Aimbot.pixel_increment
        length = int(math.dist((0, 0), (diff_x, diff_y)))
        if length == 0:
            return
        unit_x = (diff_x / length) * Aimbot.pixel_increment
        unit_y = (diff_y / length) * Aimbot.pixel_increment
        x = y = sum_x = sum_y = 0
        for k in range(0, length):
            sum_x += x
            sum_y += y
            x, y = round(unit_x * k - sum_x), round(unit_y * k - sum_y)
            yield x, y

    def start(self):
        print(Fore.CYAN + "[INFO] Beginning screen capture")
        Aimbot.update_status_aimbot()
        half_screen_width = ctypes.windll.user32.GetSystemMetrics(0) / 2
        half_screen_height = ctypes.windll.user32.GetSystemMetrics(1) / 2
        detection_box = {'left': int(half_screen_width - self.box_constant // 2),
                         'top': int(half_screen_height - self.box_constant // 2),
                         'width': int(self.box_constant),
                         'height': int(self.box_constant)}

        # Create a named window
        cv2.namedWindow("Maggu Vision", cv2.WINDOW_NORMAL)
        cv2.resizeWindow("Maggu Vision", self.box_constant, self.box_constant)

        # Set window to be transparent if in transparent mode
        if Aimbot.transparent_mode:
            hwnd = win32gui.FindWindow(None, "Maggu Vision V1")
            win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE, win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE) | win32con.WS_EX_LAYERED)
            win32gui.SetLayeredWindowAttributes(hwnd, 0, 255, win32con.LWA_ALPHA)

        while True:
            start_time = time.perf_counter()
            frame = np.array(Aimbot.screen.grab(detection_box))
            frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
            boxes = self.model.predict(source=frame, verbose=False, conf=self.conf, iou=self.iou, half=False)  # Set half=False
            result = boxes[0]

            # Create a blank image for transparent mode
            if Aimbot.transparent_mode:
                overlay = np.zeros_like(frame, dtype=np.uint8)
            else:
                overlay = frame.copy()

            if len(result.boxes.xyxy) != 0:  # Player detected
                least_crosshair_dist = closest_detection = player_in_frame = False
                for box in result.boxes.xyxy:  # Iterate over each player detected
                    x1, y1, x2, y2 = map(int, box)
                    x1y1 = (x1, y1)
                    x2y2 = (x2, y2)
                    height = y2 - y1
                    relative_head_X, relative_head_Y = int((x1 + x2) / 2), int((y1 + y2) / 2 - height / aim_height)

                    # Calculate the distance between each detection and the crosshair at (self.box_constant/2, self.box_constant/2)
                    crosshair_dist = math.dist((relative_head_X, relative_head_Y), (self.box_constant // 2, self.box_constant // 2))

                    if not least_crosshair_dist: least_crosshair_dist = crosshair_dist  # Initialize least crosshair distance variable first iteration

                    if crosshair_dist <= least_crosshair_dist:
                        least_crosshair_dist = crosshair_dist
                        closest_detection = {"x1y1": x1y1, "x2y2": x2y2, "relative_head_X": relative_head_X, "relative_head_Y": relative_head_Y}

                if closest_detection:  # If valid detection exists
                    cv2.circle(overlay, (closest_detection["relative_head_X"], closest_detection["relative_head_Y"]), 5, (115, 244, 113), -1)  # Draw circle on the head
                    cv2.line(overlay, (closest_detection["relative_head_X"], closest_detection["relative_head_Y"]),
                             (self.box_constant // 2, self.box_constant // 2), (244, 242, 113), 2)

                    absolute_head_X, absolute_head_Y = closest_detection["relative_head_X"] + detection_box['left'], closest_detection["relative_head_Y"] + detection_box['top']
                    x1, y1 = closest_detection["x1y1"]

                    if Aimbot.is_target_locked(absolute_head_X, absolute_head_Y):
                        if use_trigger_bot and not Aimbot.is_shooting():
                            Aimbot.left_click()

                        cv2.putText(overlay, "LOCKED", (x1 + 40, y1), cv2.FONT_HERSHEY_DUPLEX, 0.5, (115, 244, 113), 2)  # Draw the confidence labels on the bounding boxes
                    else:
                        cv2.putText(overlay, "TARGETING", (x1 + 40, y1), cv2.FONT_HERSHEY_DUPLEX, 0.5, (115, 113, 244), 2)  # Draw the confidence labels on the bounding boxes

                    if Aimbot.is_aimbot_enabled():
                        Aimbot.move_crosshair(self, absolute_head_X, absolute_head_Y)

            cv2.putText(overlay, f"FPS: {int(1 / (time.perf_counter() - start_time))}", (5, 30), cv2.FONT_HERSHEY_DUPLEX, 1, (113, 116, 244), 2)

            # Show the overlay
            cv2.imshow("Maggu Vision", overlay)

            # Check for key presses
            key = cv2.waitKey(1) & 0xFF
            if key == ord('0'):  # Exit on '0'
                break
            elif key == ord('3'):  # Toggle transparent mode on 'F3'
                Aimbot.toggle_transparent_mode()
                hwnd = win32gui.FindWindow(None, "Maggu Vision")
                if Aimbot.transparent_mode:
                    win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE, win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE) | win32con.WS_EX_LAYERED)
                    win32gui.SetLayeredWindowAttributes(hwnd, 0, 255, win32con.LWA_ALPHA)
                else:
                    win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE, win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE) & ~win32con.WS_EX_LAYERED)

    @staticmethod
    def clean_up():
        print(Fore.RED + "\n[INFO] F2 WAS PRESSED. QUITTING...")
        Aimbot.screen.close()
        os._exit(0)


if __name__ == "__main__":
    print(Fore.YELLOW + "You are in the wrong directory and are running the wrong file; you must run maggu.py")