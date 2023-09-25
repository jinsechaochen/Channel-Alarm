import tkinter as tk
from tkinter import Scrollbar
import cv2
import numpy as np
import threading
import time
import pyautogui
import winsound
import os
from PIL import Image, ImageTk

class DetectionApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Channel Alarm / Warning Application for EVE Online")

        self.start_button = tk.Button(root, text="开始检测", command=self.start_detection)
        self.start_button.pack()

        self.stop_button = tk.Button(root, text="停止检测", command=self.stop_detection, state=tk.DISABLED)
        self.stop_button.pack()

        self.set_region_button = tk.Button(root, text="设置检测区域", command=self.set_detection_region)
        self.set_region_button.pack()

        self.open_folder_button = tk.Button(root, text="打开记录历史文件夹", command=self.open_image_folder)
        self.open_folder_button.pack()

        self.close_button = tk.Button(root, text="关闭程序", command=self.close_program)
        self.close_button.pack()

        self.text_display = tk.Text(root, height=10, width=50, wrap=tk.WORD)  # 设置文本框高度为10，宽度为50，并允许自动换行
        self.text_display.pack()

        self.scrollbar = Scrollbar(root, command=self.text_display.yview)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.text_display.config(yscrollcommand=self.scrollbar.set)

        # 添加文本内容
        preset_text = "本软件不使用EVE Online游戏内部接口\n完全通过屏幕覆盖层方式监控屏幕上数据\n不与 EVE Online游戏官方 停用和封禁政策 \n<https://support.eveonline.com/hc/zh-cn/articles/8563815513116>发生冲突\n此软件完全开源于GitHub\n<https://github.com/jinsechaochen/Channel-Alarm>\n有新想法欢迎随时交流. \n使用本软件出现任何停用或封禁与作者无关\n"
        self.text_display.insert(tk.END, preset_text)
        self.text_display.config(state=tk.DISABLED)  # 禁止编辑

        self.detection_thread = None
        self.is_detecting = False
        self.detection_region = None
        self.draw_region = False
        self.x1, self.y1, self.x2, self.y2 = 0, 0, 0, 0
        self.warning_window = None

        self.image_folder = "warning_images"
        self.max_images = 15
        self.image_count = 0

    def set_detection_region(self):
        self.draw_region = True
        self.root.withdraw()  # 隐藏主窗口
        region_window = tk.Toplevel()
        region_window.title("设置检测区域")

        # 设置绘制窗口为半透明
        region_window.attributes("-alpha", 0.5)

        tk.Label(region_window, text="点击左上角和右下角以选择检测区域").pack()

        # 创建全屏画布
        screen_width, screen_height = pyautogui.size()
        canvas = tk.Canvas(region_window, width=screen_width, height=screen_height)
        canvas.pack()

        # 初始化矩形坐标
        self.x1, self.y1, self.x2, self.y2 = 0, 0, 0, 0

        def on_mouse_down(event):
            nonlocal self
            self.x1, self.y1 = event.x, event.y

        def on_mouse_drag(event):
            nonlocal self
            if self.draw_region:
                self.x2, self.y2 = event.x, event.y
                canvas.delete("rect")  # 删除之前的矩形
                canvas.create_rectangle(self.x1, self.y1, self.x2, self.y2, outline="red", tags="rect")

        def on_mouse_up(event):
            nonlocal self
            self.x2, self.y2 = event.x, event.y
            self.detection_region = (self.x1, self.y1, self.x2, self.y2)
            self.draw_region = False
            region_window.destroy()
            self.root.deiconify()  # 显示主窗口

        canvas.bind("<ButtonPress-1>", on_mouse_down)
        canvas.bind("<B1-Motion>", on_mouse_drag)
        canvas.bind("<ButtonRelease-1>", on_mouse_up)
        region_window.mainloop()

    def open_image_folder(self):
        if os.path.exists(self.image_folder):
            os.startfile(self.image_folder)

    def start_detection(self):
        if not self.is_detecting:
            self.is_detecting = True
            self.start_button.config(state=tk.DISABLED)
            self.stop_button.config(state=tk.NORMAL)
            self.detection_thread = threading.Thread(target=self.detect_red_color)
            self.detection_thread.start()

    def stop_detection(self):
        if self.is_detecting:
            self.is_detecting = False
            self.start_button.config(state=tk.NORMAL)
            self.stop_button.config(state=tk.DISABLED)
            if self.detection_thread:
                self.detection_thread.join()

    def detect_red_color(self):
        while self.is_detecting:
            if self.detection_region:
                screenshot = self.capture_screen()
                x1, y1, x2, y2 = self.detection_region
                region = screenshot[y1:y2, x1:x2]  # 仅在检测区域内进行检测
                hsv = cv2.cvtColor(region, cv2.COLOR_BGR2HSV)
                lower_red = np.array([0, 100, 100])
                upper_red = np.array([10, 255, 255])
                mask = cv2.inRange(hsv, lower_red, upper_red)
                red_pixel_count = cv2.countNonZero(mask)

                if red_pixel_count > 0 and not self.warning_window:
                    current_time = time.strftime("%Y-%m-%d %H:%M:%S")
                    message = f"[{current_time}] 警告！潜在敌人出现！请注意！\n"
                    self.text_display.config(state=tk.NORMAL)  # 允许编辑
                    self.text_display.insert(tk.END, message)
                    self.text_display.see(tk.END)
                    self.text_display.config(state=tk.DISABLED)  # 禁止编辑
                    self.warning_window = self.display_warning_on_screen(region)

                    # 播放声音警报
                    winsound.Beep(1000, 1500)  # 使用Beep函数播放声音，1000Hz的声音，持续1.5秒

                    # 保存红色图片
                    if self.image_count < self.max_images:
                        image_filename = os.path.join(self.image_folder, f"warning_{self.image_count}.png")
                        cv2.imwrite(image_filename, region)
                        self.image_count += 1
                elif red_pixel_count == 0 and self.warning_window:
                    self.warning_window.destroy()
                    self.warning_window = None

    def capture_screen(self):
        screenshot = pyautogui.screenshot()
        screenshot = np.array(screenshot)
        screenshot = cv2.cvtColor(screenshot, cv2.COLOR_RGB2BGR)
        return screenshot

    def display_warning_on_screen(self, region):
        overlay = region.copy()
        cv2.putText(overlay, "警告", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 2, (0, 0, 255), 2)
        cv2.addWeighted(overlay, 0.5, region, 1 - 0.5, 0, region)  # 添加半透明的覆盖层

        warning_window = tk.Toplevel()
        warning_window.title("警告")
        warning_window.attributes("-topmost", True)  # 窗口置于顶层

        cv2image = cv2.cvtColor(region, cv2.COLOR_BGR2RGB)
        img = Image.fromarray(cv2image)
        photo = ImageTk.PhotoImage(image=img)

        label = tk.Label(warning_window, image=photo)
        label.image = photo
        label.pack()

        return warning_window

    def close_program(self):
        self.root.quit()

if __name__ == "__main__":
    root = tk.Tk()
    app = DetectionApp(root)
    root.mainloop()
