import tkinter as tk
import threading
import time
import os
from PIL import ImageGrab
import pytesseract
import pyautogui
from google import genai
import pyttsx3
from dotenv import load_dotenv

# ==========================================
# CONFIGURATION
# ==========================================
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'


# ==========================================
# SCREEN SELECTION OVERLAY COMPONENT
# ==========================================
class RegionSelectorOverlay:
    def __init__(self, root_window, callback):
        self.root = root_window
        self.callback = callback
        
        self.top = tk.Toplevel(self.root)
        self.top.attributes("-fullscreen", True)
        self.top.attributes("-alpha", 0.3)
        self.top.config(cursor="cross")
        
        self.canvas = tk.Canvas(self.top, cursor="cross", bg="black")
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
        self.rect = self.canvas.create_rectangle(self.start_x, self.start_y, 1, 1, outline='#00FF00', width=2)

    def on_move_press(self, event):
        cur_x, cur_y = (event.x, event.y)
        self.canvas.coords(self.rect, self.start_x, self.start_y, cur_x, cur_y)

    def on_button_release(self, event):
        end_x, end_y = (event.x, event.y)
        
        x1 = min(self.start_x, end_x)
        y1 = min(self.start_y, end_y)
        x2 = max(self.start_x, end_x)
        y2 = max(self.start_y, end_y)
        
        width = x2 - x1
        height = y2 - y1
        self.top.destroy()
        
        if width > 5 and height > 5:
            self.callback((x1, y1, x2, y2))


# ==========================================
# MAIN APPLICATION CLASS
# ==========================================
class AutoQuizSolverApp:
    def __init__(self, root_window):
        self.root = root_window
        self.root.title("ACLC Malolos Fully Auto Quiz Solver")
        self.root.geometry("360x540+50+50")
        self.root.attributes("-topmost", True)
        self.root.resizable(False, False)
        self.root.config(bg="black")

        # Application States
        self.selected_region = None  
        self.next_button_coord = None  
        self.choice_coords = {} 
        self.is_running = False
        self.marker_window = None 
        self.status_message = "Awaiting configuration"
        self.is_scanned = False

        # Initialize Text-to-Speech Engine
        try:
            self.tts_engine = pyttsx3.init()
            self.tts_engine.setProperty('rate', 165)
        except Exception as e:
            self.tts_engine = None

        # Initialize Gemini Client
        try:
            self.client = genai.Client(api_key=GEMINI_API_KEY) if GEMINI_API_KEY else None
        except Exception as e:
            self.client = None

        self.create_widgets()
        self.start_animation_loop()

    def speak(self, text):
        if self.tts_engine and self.var_voice.get():
            def run_speech():
                try:
                    engine = pyttsx3.init()
                    engine.setProperty('rate', 165)
                    engine.say(text)
                    engine.runAndWait()
                except Exception as e:
                    print(f"TTS Error: {e}")
            threading.Thread(target=run_speech, daemon=True).start()

    def show_click_marker(self, x, y):
        def draw_marker():
            top = tk.Toplevel(self.root)
            top.overrideredirect(True)
            top.attributes("-topmost", True)
            top.attributes("-alpha", 0.7)
            size = 30
            top.geometry(f"{size}x{size}+{x - size//2}+{y - size//2}")
            
            canvas = tk.Canvas(top, width=size, height=size, bg="black", highlightthickness=0)
            canvas.pack(fill="both", expand=True)
            canvas.create_oval(2, 2, size-2, size-2, outline="#FF0000", width=4, fill="#550000")
            top.after(800, top.destroy)

        self.root.after(0, draw_marker)

    def create_widgets(self):
        lbl_title = tk.Label(
            self.root, 
            text="[ FULLY AUTO QUIZ SOLVER ]", 
            font=("Consolas", 11, "bold"), 
            bg="black", 
            fg="#00FF00"
        )
        lbl_title.pack(pady=(8, 2))

        lbl_warning = tk.Label(
            self.root, 
            text="PROTOTYPE - USE AT YOUR OWN RISK", 
            font=("Consolas", 7, "bold"), 
            bg="black", 
            fg="#FF0000", 
            justify="center"
        )
        lbl_warning.pack(pady=(0, 6))

        # Button 1: Region Selector
        self.btn_select = tk.Button(
            self.root, text="1. Select Quiz Region", 
            font=("Consolas", 9, "bold"), bg="#051c0d", fg="#00FF00", 
            activebackground="#00FF00", activeforeground="black", 
            bd=1, relief="solid", width=34, height=1, 
            command=self.trigger_quiz_selection
        )
        self.btn_select.pack(pady=3)

        # Button 2: Set Choice Coordinates (A, B, C, D)
        self.btn_choices = tk.Button(
            self.root, text="2. Set Choice Coordinates (A,B,C,D)", 
            font=("Consolas", 9, "bold"), bg="#051c0d", fg="#00FF00", 
            activebackground="#00FF00", activeforeground="black", 
            bd=1, relief="solid", width=34, height=1, 
            command=self.pick_choice_coordinates
        )
        self.btn_choices.pack(pady=3)

        # Button 3: Next Button Coordinate Setter
        self.btn_next_coord = tk.Button(
            self.root, text="3. Set 'Next' Button", 
            font=("Consolas", 9, "bold"), bg="#051c0d", fg="#00FF00", 
            activebackground="#00FF00", activeforeground="black", 
            bd=1, relief="solid", width=34, height=1, 
            command=self.pick_next_button_coord
        )
        self.btn_next_coord.pack(pady=3)

        # Undo / Reset Button
        self.btn_undo = tk.Button(
            self.root, text="🔄 Undo / Reset", 
            font=("Consolas", 9, "bold"), bg="#1c1300", fg="#00FF00", 
            activebackground="#00FF00", activeforeground="black", 
            bd=1, relief="solid", width=34, height=1, 
            command=self.undo_settings
        )
        self.btn_undo.pack(pady=3)

        # Auto-Next Checkbox
        self.var_auto_next = tk.IntVar(value=1)
        self.chk_auto_next = tk.Checkbutton(
            self.root, text="Auto-Click 'Next' After Answering", 
            variable=self.var_auto_next, font=("Consolas", 9), 
            bg="black", fg="#00FF00", selectcolor="black", 
            activebackground="black", activeforeground="#00FF00"
        )
        self.chk_auto_next.pack(anchor="w", padx=20, pady=2)

        # Voice Reader Checkbox
        self.var_voice = tk.IntVar(value=1)
        self.chk_voice = tk.Checkbutton(
            self.root, text="Basaing Boses (Voice Reader)", 
            variable=self.var_voice, font=("Consolas", 9), 
            bg="black", fg="#00FF00", selectcolor="black", 
            activebackground="black", activeforeground="#00FF00"
        )
        self.chk_voice.pack(anchor="w", padx=20, pady=2)

        # Start/Stop Button
        self.btn_toggle = tk.Button(
            self.root, text="4. START FULL AUTO SOLVER", 
            font=("Consolas", 9, "bold"), bg="#111111", fg="#444444", 
            activebackground="#00FF00", activeforeground="black", 
            bd=1, relief="solid", width=34, height=1, 
            command=self.toggle_scanner, state=tk.DISABLED
        )
        self.btn_toggle.pack(pady=4)

        # Log Text Box Area
        self.text_log = tk.Text(
            self.root, height=5, width=40, 
            font=("Consolas", 9), bg="black", fg="#00FF00", 
            insertbackground="#00FF00", bd=1, relief="solid"
        )
        self.text_log.pack(padx=10, pady=4)
        self.text_log.config(state=tk.DISABLED)

    def update_log(self, text):
        def _update():
            self.text_log.config(state=tk.NORMAL)
            self.text_log.delete("1.0", tk.END)
            self.text_log.insert(tk.END, text)
            self.text_log.config(state=tk.DISABLED)
        self.root.after(0, _update)

    def start_animation_loop(self):
        def animate():
            dot_count = 0
            while True:
                if not self.is_running:
                    dots = "." * ((dot_count % 3) + 1)
                    if self.is_scanned:
                        msg = f">> Ready to Auto-Solve{dots}"
                    else:
                        msg = f">> Awaiting configuration{dots}"
                    self.update_log(msg)
                    dot_count += 1
                time.sleep(0.5)
        threading.Thread(target=animate, daemon=True).start()

    def trigger_quiz_selection(self):
        RegionSelectorOverlay(self.root, self.on_quiz_region_selected)

    def on_quiz_region_selected(self, region):
        self.selected_region = region
        self.is_scanned = True
        self.check_enable_start()

    def check_enable_start(self):
        if self.selected_region and len(self.choice_coords) > 0:
            self.btn_toggle.config(state=tk.NORMAL, bg="#003300", fg="#00FF00")

    def pick_choice_coordinates(self):
        choices = ['A', 'B', 'C', 'D']
        self.choice_coords.clear()
        
        def prompt_next_choice(index=0):
            if index >= len(choices):
                self.update_log(">> All choices successfully mapped!")
                self.check_enable_start()
                return
                
            current_choice = choices[index]
            self.update_log(f">> Click the position of Choice [{current_choice}]...")
            
            picker_win = tk.Toplevel(self.root)
            picker_win.attributes("-fullscreen", True)
            picker_win.attributes("-alpha", 0.1)
            picker_win.config(cursor="target")
            
            def on_click_coord(event):
                self.choice_coords[current_choice] = (event.x_root, event.y_root)
                picker_win.destroy()
                prompt_next_choice(index + 1)
                
            picker_win.bind("<Button-1>", on_click_coord)

        prompt_next_choice(0)

    def pick_next_button_coord(self):
        self.update_log(">> Click the 'Next' button position...")
        picker_win = tk.Toplevel(self.root)
        picker_win.attributes("-fullscreen", True)
        picker_win.attributes("-alpha", 0.1)
        picker_win.config(cursor="target")
        
        def on_click_coord(event):
            self.next_button_coord = (event.x_root, event.y_root)
            picker_win.destroy()
            self.update_log(">> 'Next' button coordinate saved!")

        picker_win.bind("<Button-1>", on_click_coord)

    def toggle_scanner(self):
        if not self.selected_region or not self.choice_coords:
            self.update_log(">> Error: Incomplete configuration!")
            return
            
        if not self.client:
            self.update_log(">> Error: Missing GEMINI_API_KEY in .env!")
            return

        if not self.is_running:
            self.is_running = True
            self.btn_toggle.config(text="STOP AUTO SOLVER", bg="#330000", fg="#FF0000")
            threading.Thread(target=self.run_auto_solver_loop, daemon=True).start()
        else:
            self.is_running = False
            self.btn_toggle.config(text="4. START FULL AUTO SOLVER", bg="#051c0d", fg="#00FF00")

    def ask_gemini_for_answer(self, question_text):
        try:
            response = self.client.models.generate_content(
                model="gemini-2.5-flash",
                contents=f"You are an expert quiz solver. Return ONLY a single letter choice: A, B, C, or D corresponding to the correct answer. No extra words or characters.\n\nQuestion and choices:\n{question_text}"
            )
            raw_answer = response.text
            cleaned = "".join([c for c in raw_answer.upper() if c in ['A', 'B', 'C', 'D']])
            return cleaned[0] if cleaned else None
        except Exception as e:
            print(f"Gemini Error: {e}")
            return None

    def run_auto_solver_loop(self):
        print("Auto Solver loop started with Gemini...")
        last_detected_text = ""
        
        while self.is_running:
            try:
                if self.selected_region:
                    screenshot = ImageGrab.grab(bbox=self.selected_region)
                    detected_text = pytesseract.image_to_string(screenshot).strip()
                    
                    if detected_text and detected_text != last_detected_text:
                        last_detected_text = detected_text
                        self.update_log(">> New question detected...")
                        
                        clean_speech_text = detected_text.replace('\n', ' ')
                        self.speak("Bagong tanong: " + clean_speech_text)
                        
                        ai_choice = self.ask_gemini_for_answer(detected_text)
                        print(f"DEBUG: Detected AI Choice -> [{ai_choice}] | Available Coords: {list(self.choice_coords.keys())}")
                        
                        if ai_choice and ai_choice in self.choice_coords:
                            self.update_log(f">> AI Answer: [{ai_choice}] -> Clicking...")
                            self.speak(f"Ang sagot ay titik {ai_choice}")
                            
                            coord = self.choice_coords[ai_choice]
                            self.show_click_marker(coord[0], coord[1])
                            
                            pyautogui.click(coord[0], coord[1])
                            time.sleep(1)
                            
                            if self.var_auto_next.get() and self.next_button_coord:
                                self.show_click_marker(self.next_button_coord[0], self.next_button_coord[1])
                                pyautogui.click(self.next_button_coord[0], self.next_button_coord[1])
                                time.sleep(1.5)
                                last_detected_text = ""
                        else:
                            self.update_log(f">> Failed to parse valid choice: {ai_choice}")
                    else:
                        self.update_log(">> Waiting for question / Next...")
                else:
                    break
                    
                time.sleep(1.5)
            except Exception as e:
                print(f"Loop Exception: {e}")
                self.update_log(f">> Error: {str(e)}\n")
                break

    def undo_settings(self):
        if self.is_running:
            self.is_running = False
            self.btn_toggle.config(text="4. START FULL AUTO SOLVER", bg="#051c0d", fg="#00FF00")
            
        self.selected_region = None
        self.next_button_coord = None
        self.choice_coords.clear()
        self.is_scanned = False
        
        if self.marker_window:
            self.marker_window.destroy()
            self.marker_window = None
            
        self.btn_toggle.config(state=tk.DISABLED, bg="#111111", fg="#444444")


# ==========================================
# MAIN EXECUTION ENTRY POINT
# ==========================================
if __name__ == "__main__":
    root = tk.Tk()
    app = AutoQuizSolverApp(root)
    root.mainloop()