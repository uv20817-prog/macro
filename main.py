import tkinter as tk
import mss
import requests
import base64
import os
import traceback
from io import BytesIO
from PIL import Image

RESULT_FILE = os.path.join(os.environ['USERPROFILE'], 'OneDrive', 'Desktop', 'macro', 'result.txt')

class Selector:
    def __init__(self):
        try:
            self.win = tk.Tk()
            self.win.attributes('-fullscreen', True)
            self.win.attributes('-alpha', 0.3)
            self.win.configure(bg='black')
            self.win.attributes('-topmost', True)
            
            self.canvas = tk.Canvas(self.win, bg='black', highlightthickness=0)
            self.canvas.pack(fill=tk.BOTH, expand=True)
            
            self.canvas.bind('<Button-1>', self.on_down)
            self.canvas.bind('<B1-Motion>', self.on_drag)
            self.canvas.bind('<ButtonRelease-1>', self.on_up)
            self.win.bind('<Escape>', lambda e: self.win.destroy())
            
            self.win.focus_force()
            self.win.mainloop()
        except Exception as e:
            open(RESULT_FILE, "w", encoding="utf-8").write(f"ERR_INIT: {str(e)}\n{traceback.format_exc()}")

    def on_down(self, event):
        self.start_x = event.x
        self.start_y = event.y
        self.rect = self.canvas.create_rectangle(event.x, event.y, event.x, event.y, outline='red', width=3)

    def on_drag(self, event):
        self.canvas.coords(self.rect, self.start_x, self.start_y, event.x, event.y)

    def on_up(self, event):
        x1 = min(self.start_x, event.x)
        y1 = min(self.start_y, event.y)
        x2 = max(self.start_x, event.x)
        y2 = max(self.start_y, event.y)
        
        if abs(x2-x1) > 10 and abs(y2-y1) > 10:
            self.win.destroy()
            self.process(x1, y1, x2, y2)
        else:
            self.win.destroy()

    def process(self, x1, y1, x2, y2):
        try:
            with mss.mss() as sct:
                monitor = {"left": int(x1), "top": int(y1), "width": int(x2-x1), "height": int(y2-y1)}
                screenshot = sct.grab(monitor)
                img = Image.frombytes('RGB', screenshot.size, screenshot.bgra, 'raw', 'BGRX')
                
                img.thumbnail((1024, 1024))
                
                buffer = BytesIO()
                img.save(buffer, format='PNG')
                img_data = base64.b64encode(buffer.getvalue()).decode('utf-8')

            url = "http://localhost:1234/v1/chat/completions"
            payload = {
                "model": "google/gemma-4-e4b",
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": "Опиши что на картинке."},
                            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img_data}"}}
                        ]
                    }
                ],
                "max_tokens": 500
            }
            
            response = requests.post(url, json=payload, timeout=120)
            
            if response.status_code == 200:
                result = response.json()
                content = result.get('choices', [{}])[0].get('message', {}).get('content', '')
                open(RESULT_FILE, "w", encoding="utf-8").write(content if content else "Пустой ответ")
            else:
                open(RESULT_FILE, "w", encoding="utf-8").write(f"HTTP {response.status_code}: {response.text[:200]}")
                    
        except Exception as e:
            open(RESULT_FILE, "w", encoding="utf-8").write(f"ERR: {str(e)}\n{traceback.format_exc()}")

if __name__ == "__main__":
    Selector()