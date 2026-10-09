import ctypes
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except:
        pass

import tkinter as tk
from tkinter import simpledialog
import pyautogui
import json
import os
import time
import pytesseract
from pytesseract import Output
from PIL import Image

# Path to Tesseract OCR engine on Windows
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

class QuizSolverApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Python Automatic LMS")
        self.root.geometry("320x450")
        self.root.config(bg="black")
        self.root.attributes("-topmost", True)

        title_label = tk.Label(root, text="[ FULLY AUTO QUIZ SOLVER ]", fg="#00FF00", bg="black", font=("Courier", 11, "bold"))
        title_label.pack(pady=15)

        subtitle_label = tk.Label(root, text="PROTOTYPE - LOCAL PYTHON APP", fg="red", bg="black", font=("Arial", 8, "bold"))
        subtitle_label.pack(pady=2)

        self.btn_region = tk.Button(root, text="1. Select Region & Auto-Click", fg="#00FF00", bg="#112211", 
                                    font=("Courier", 9, "bold"), relief="solid", bd=1, command=self.start_selection)
        self.btn_region.pack(fill="x", padx=20, pady=10)

        self.btn_db = tk.Button(root, text="2. Load Local Database", fg="#00FF00", bg="#112211", 
                                font=("Courier", 10, "bold"), relief="solid", bd=1, command=self.load_database)
        self.btn_db.pack(fill="x", padx=20, pady=10)

        self.status_label = tk.Label(root, text=">> Awaiting configuration..", fg="#00FF00", bg="black", 
                                     font=("Courier", 9), anchor="w", justify="left", wraplength=280)
        self.status_label.pack(fill="x", padx=20, pady=15)

        self.questions_db = {}
        self.init_database()

    def init_database(self):
        if not os.path.exists("database.json"):
            sample_data = {
                "An employee at a branch office is creating a quote for a customer. In order to do this, the employee needs to access confidential pricing information from internal servers at the Head Office. What type of network would the employee access?": "intranet"
            }
            with open("database.json", "w", encoding="utf-8") as f:
                json.dump(sample_data, f, indent=4, ensure_ascii=False)
        self.load_database()

    def load_database(self):
        try:
            with open("database.json", "r", encoding="utf-8") as f:
                self.questions_db = json.load(f)
            self.status_label.config(text=f">> DB Loaded: {len(self.questions_db)} questions.")
        except Exception as e:
            self.status_label.config(text=f">> Error loading DB: {str(e)}")

    def save_to_database(self, question, answer):
        q_clean = question.strip()
        a_clean = answer.strip()
        if q_clean and a_clean:
            self.questions_db[q_clean] = a_clean
            try:
                with open("database.json", "w", encoding="utf-8") as f:
                    json.dump(self.questions_db, f, indent=4, ensure_ascii=False)
                return True
            except Exception as e:
                print(f"Failed to save: {e}")
        return False

    def start_selection(self):
        self.root.withdraw()
        
        self.overlay = tk.Toplevel(self.root)
        self.overlay.attributes("-alpha", 0.3)
        self.overlay.attributes("-fullscreen", True)
        self.overlay.config(cursor="cross")

        self.canvas = tk.Canvas(self.overlay, cursor="cross", bg="grey")
        self.canvas.pack(fill="both", expand=True)

        self.canvas.bind("<ButtonPress-1>", self.on_button_press)
        self.canvas.bind("<B1-Motion>", self.on_move_press)
        self.canvas.bind("<ButtonRelease-1>", self.on_button_release)

        self.start_x = None
        self.start_y = None
        self.rect = None

    def on_button_press(self, event):
        self.start_x = event.x
        self.start_y = event.y
        self.rect = self.canvas.create_rectangle(self.start_x, self.start_y, 1, 1, outline='lime', width=2)

    def on_move_press(self, event):
        cur_x, cur_y = (event.x, event.y)
        self.canvas.coords(self.rect, self.start_x, self.start_y, cur_x, cur_y)

    def on_button_release(self, event):
        end_x = event.x
        end_y = event.y
        self.overlay.destroy()
        self.root.deiconify()

        x1 = min(self.start_x, end_x)
        y1 = min(self.start_y, end_y)
        width = abs(end_x - self.start_x)
        height = abs(end_y - self.start_y)

        if width > 10 and height > 10:
            screenshot = pyautogui.screenshot(region=(x1, y1, width, height))
            
            try:
                ocr_data = pytesseract.image_to_data(screenshot, output_type=Output.DICT)
                
                extracted_words = [ocr_data['text'][i] for i in range(len(ocr_data['text'])) if ocr_data['text'][i].strip()]
                clean_question = " ".join(extracted_words)
                
                if not clean_question:
                    self.status_label.config(text=">> No text detected!")
                    return

                self.status_label.config(text=f">> Read: {clean_question[:30]}...")
                self.root.update()
                
                # Matching check
                found_answer = None
                for q, a in self.questions_db.items():
                    if q.strip().lower() in clean_question.strip().lower() or clean_question.strip().lower() in q.strip().lower():
                        found_answer = a
                        break
                
                if not found_answer:
                    for q, a in self.questions_db.items():
                        db_words = [w.lower() for w in q.split() if len(w) > 4]
                        matches = sum(1 for w in db_words if w in clean_question.lower())
                        if matches >= 2:
                            found_answer = a
                            break

                if found_answer:
                    self.status_label.config(text=f">> FOUND: {found_answer}")
                    self.root.update()
                else:
                    self.status_label.config(text=">> Not in DB! Prompting...")
                    self.root.update()
                    self.root.attributes("-topmost", False)
                    user_answer = simpledialog.askstring("New Question", "Enter correct answer:")
                    self.root.attributes("-topmost", True)
                    
                    if user_answer:
                        if self.save_to_database(clean_question[:100], user_answer):
                            found_answer = user_answer
                        else:
                            return
                    else:
                        return

                # Paghahanap at pag-click sa screen
                answers_list = [ans.strip().lower() for ans in found_answer.split(",")]
                clicked_count = 0
                
                for target_word in answers_list:
                    target_x, target_y = None, None
                    for i in range(len(ocr_data['text'])):
                        word = ocr_data['text'][i].lower().strip()
                        if target_word in word or word in target_word:
                            bx = ocr_data['left'][i]
                            by = ocr_data['top'][i]
                            bh = ocr_data['height'][i]
                            
                            row_lefts = []
                            for j in range(len(ocr_data['text'])):
                                if ocr_data['text'][j].strip():
                                    if abs(ocr_data['top'][j] - by) < 15:
                                        row_lefts.append(ocr_data['left'][j])
                            
                            if row_lefts:
                                min_left = min(row_lefts)
                                target_x = x1 + max(5, min_left - 15)
                            else:
                                target_x = x1 + bx - 25
                                
                            target_y = y1 + by + (bh // 2)
                            break
                    
                    if target_x and target_y:
                        pyautogui.click(target_x, target_y)
                        clicked_count += 1
                        time.sleep(0.3)

                if clicked_count > 0:
                    self.status_label.config(text=f">> Clicked successfully ({clicked_count})!")
                else:
                    self.status_label.config(text=f">> Click failed: Word not matched.")
                    
            except Exception as e:
                self.status_label.config(text=f">> Error: {str(e)}")
        else:
            self.status_label.config(text=">> Region too small.")

if __name__ == "__main__":
    root = tk.Tk()
    app = QuizSolverApp(root)
    root.mainloop()