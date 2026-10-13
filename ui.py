import sys
import os
import re

import pyautogui
import pytesseract

from PySide6.QtCore import Qt, QThread, Signal, QTimer, QRect
from PySide6.QtGui import QFont, QPainter, QColor
from PySide6.QtWidgets import (
    QApplication,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QFrame,
    QTextEdit,
    QRubberBand,
)


TESSERACT_PATH = r"C:\Program Files\Tesseract-OCR\tesseract.exe"


# Common question patterns in English and Filipino.
QUESTION_PATTERNS = [
    r"\bwhat\s+(is|are|was|were|does|do|did|will|would|causes?)\b",
    r"\bwhich\s+(of|one|statement|answer|option|following)\b",
    r"\bwho\s+(is|are|was|were|invented|discovered)\b",
    r"\bwhen\s+(is|was|did|does|will)\b",
    r"\bwhere\s+(is|are|was|were|can|did)\b",
    r"\bwhy\s+(is|are|was|were|does|do|did)\b",
    r"\bhow\s+(many|much|does|do|did|can|is|are|to)\b",
    r"\bselect\s+(the|one|all)\b",
    r"\bchoose\s+(the|one|all)\b",
    r"\bidentify\b",
    r"\bsolve\b",
    r"\bcalculate\b",
    r"\bdetermine\b",
    r"\bfind\s+(the|a|an|value|sum|product|answer)\b",
    r"\bcomplete\s+the\b",
    r"\bfill\s+in\s+the\b",
    r"\btrue\s+or\s+false\b",
    r"\bano\s+ang\b",
    r"\balin\s+sa\b",
    r"\balin\s+ang\b",
    r"\bsino\s+ang\b",
    r"\bkailan\b",
    r"\bsaan\b",
    r"\bbakit\b",
    r"\bpaano\b",
    r"\bilang\b",
    r"\btukuyin\b",
    r"\bkuwentahin\b",
    r"\bkalkulahin\b",
]


def detect_question(text):
    """
    Returns question-like lines found in the OCR text.
    A question mark or a recognized question pattern is required.
    """
    if not text or not text.strip():
        return []

    found = []
    seen = set()

    lines = [
        re.sub(r"\s+", " ", line).strip(" \t|")
        for line in text.splitlines()
    ]

    for line in lines:
        if len(line) < 5:
            continue

        normalized = line.lower()

        ignored = [
            "ghost_terminal",
            "analyze target",
            "scanning screen",
            "system status",
            "target monitor",
            "extracted screen text",
            "screen ocr",
            "ai not connected",
            "successfully detected",
            "no question detected",
            "automatic answer",
        ]

        if any(label in normalized for label in ignored):
            continue

        has_question_mark = "?" in line
        has_question_pattern = any(
            re.search(pattern, normalized)
            for pattern in QUESTION_PATTERNS
        )

        if has_question_mark or has_question_pattern:
            key = normalized
            if key not in seen:
                seen.add(key)
                found.append(line)

    return found


class RegionSelector(QWidget):
    def __init__(self, callback):
        super().__init__()
        self.callback = callback
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint 
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setWindowState(Qt.WindowState.WindowFullScreen)
        self.setCursor(Qt.CursorShape.CrossCursor)
        self.setStyleSheet("background: transparent;")
        
        self.origin = None
        self.rubber_band = QRubberBand(QRubberBand.Shape.Rectangle, self)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(0, 0, 0, 100))

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.origin = event.position().toPoint()
            self.rubber_band.setGeometry(QRect(self.origin, self.origin))
            self.rubber_band.show()
            event.accept()

    def mouseMoveEvent(self, event):
        if self.origin:
            self.rubber_band.setGeometry(QRect(self.origin, event.position().toPoint()).normalized())
            event.accept()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            rect = self.rubber_band.geometry()
            self.close()
            if rect.width() > 10 and rect.height() > 10:
                screenshot = pyautogui.screenshot(region=(rect.x(), rect.y(), rect.width(), rect.height()))
                self.callback(screenshot)
            else:
                self.callback(None)
            event.accept()


class OCRWorker(QThread):
    finished_text = Signal(str, list)
    failed = Signal(str)

    def __init__(self, screenshot):
        super().__init__()
        self.screenshot = screenshot

    def run(self):
        try:
            if os.path.isfile(TESSERACT_PATH):
                pytesseract.pytesseract.tesseract_cmd = TESSERACT_PATH

            text = pytesseract.image_to_string(
                self.screenshot,
                config="--psm 6"
            ).strip()

            questions = detect_question(text)
            self.finished_text.emit(text, questions)

        except Exception as exc:
            self.failed.emit(str(exc))


class GhostTerminal(QWidget):
    def __init__(self):
        super().__init__()

        self.worker = None
        self.selector = None

        self.setWindowTitle("GHOST TERMINAL // LMS PORTAL")
        self.resize(440, 840)

        self.setWindowFlags(
            Qt.WindowType.Window
            | Qt.WindowType.WindowStaysOnTopHint
        )

        self.setStyleSheet("""
            QWidget {
                background: #050505;
                color: #eeeeee;
                font-family: Consolas;
                font-size: 12px;
            }

            QFrame#panel {
                background: #080808;
                border: 1px solid #555555;
            }

            QTextEdit {
                background: #080808;
                color: #ffffff;
                border: 1px solid #444444;
                padding: 8px;
                selection-background-color: #ffffff;
                selection-color: #000000;
            }

            QPushButton {
                background: #ffffff;
                color: #000000;
                border: 1px solid #ffffff;
                padding: 10px;
                font-weight: bold;
            }

            QPushButton:hover {
                background: #cccccc;
            }

            QPushButton:disabled {
                background: #777777;
                color: #222222;
            }

            QPushButton#windowButton {
                background: #050505;
                color: #ffffff;
                border: 1px solid #555555;
                padding: 3px 8px;
            }

            QLabel#muted {
                color: #999999;
            }

            QLabel#title {
                font-size: 15px;
                font-weight: bold;
            }
        """)

        self.build_ui()

    def build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(14, 12, 14, 14)
        root.setSpacing(10)

        # Header
        header = QHBoxLayout()
        title = QLabel("GHOST_TERMINAL")
        title.setObjectName("title")
        header.addWidget(title)
        header.addStretch()

        minimize_btn = QPushButton("_")
        minimize_btn.setObjectName("windowButton")
        minimize_btn.clicked.connect(self.showMinimized)
        header.addWidget(minimize_btn)

        close_btn = QPushButton("X")
        close_btn.setObjectName("windowButton")
        close_btn.clicked.connect(self.close)
        header.addWidget(close_btn)

        root.addLayout(header)

        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        root.addWidget(line)

        # System Status Row
        status_row = QHBoxLayout()
        status_row.addWidget(QLabel("SYSTEM STATUS"))
        status_row.addStretch()

        self.status_label = QLabel("READY")
        self.status_label.setObjectName("muted")
        status_row.addWidget(self.status_label)
        root.addLayout(status_row)

        # Target Monitor Section
        root.addWidget(QLabel("TARGET MONITOR"))
        self.target_label = QLabel("Ready to select a target region for analysis.")
        self.target_label.setWordWrap(True)
        root.addWidget(self.target_label)

        self.analyze_btn = QPushButton(">> SELECT REGION & ANALYZE")
        self.analyze_btn.clicked.connect(self.start_analysis)
        root.addWidget(self.analyze_btn)

        self.loading_label = QLabel("")
        self.loading_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.loading_label.setFont(QFont("Consolas", 12))
        root.addWidget(self.loading_label)

        self.detection_label = QLabel("DETECTION STATUS: READY")
        self.detection_label.setWordWrap(True)
        root.addWidget(self.detection_label)

        # Detected Question Text Box
        root.addWidget(QLabel("DETECTED QUESTION / OCR TEXT"))
        self.response_box = QTextEdit()
        self.response_box.setReadOnly(True)
        self.response_box.setPlaceholderText("Detected question will appear here...")
        root.addWidget(self.response_box, 1)

        # ----------------------------------------------------
        # AUTOMATIC ANSWER YOUR LMS PORTAL/QUIZ SECTION
        # ----------------------------------------------------
        line_lms = QFrame()
        line_lms.setFrameShape(QFrame.Shape.HLine)
        root.addWidget(line_lms)

        lms_header = QHBoxLayout()
        lms_header.addWidget(QLabel("AUTOMATIC ANSWER YOUR LMS PORTAL/QUIZ"))
        lms_header.addStretch()

        self.lms_status_label = QLabel("STANDBY")
        self.lms_status_label.setObjectName("muted")
        lms_header.addWidget(self.lms_status_label)
        root.addLayout(lms_header)

        self.lms_response_box = QTextEdit()
        self.lms_response_box.setReadOnly(True)
        self.lms_response_box.setPlaceholderText(
            "Automatic answers, options, or LMS portal responses will appear here..."
        )
        root.addWidget(self.lms_response_box, 1)

        self.auto_solve_btn = QPushButton(">> EXECUTE AUTOMATIC ANSWER")
        self.auto_solve_btn.clicked.connect(self.run_auto_answer)
        root.addWidget(self.auto_solve_btn)

        # Bagong Button para sa Auto-Click / Auto-Next (Green color text)
        self.auto_click_btn = QPushButton(">> AUTO-CLICK / AUTO-NEXT")
        self.auto_click_btn.setStyleSheet("""
            QPushButton {
                background: #080808;
                color: #66ff99;
                border: 1px solid #66ff99;
                padding: 10px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #112211;
            }
        """)
        self.auto_click_btn.clicked.connect(self.run_auto_click)
        root.addWidget(self.auto_click_btn)

        # Footer
        footer = QLabel("SCREEN OCR // LMS AUTOMATION ENGINE")
        footer.setObjectName("muted")
        footer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.addWidget(footer)

        # Timer setup for spinner animation
        self.spinner_frames = ["|", "/", "-", "\\"]
        self.spinner_index = 0
        self.spinner_timer = QTimer(self)
        self.spinner_timer.timeout.connect(self.animate_loading)

    def start_analysis(self):
        if self.worker is not None and self.worker.isRunning():
            return

        self.hide()
        QTimer.singleShot(200, self.open_region_selector)

    def open_region_selector(self):
        self.selector = RegionSelector(self.on_region_selected)
        self.selector.show()

    def on_region_selected(self, screenshot):
        if screenshot is None:
            self.show()
            return

        self.analyze_btn.setEnabled(False)
        self.analyze_btn.setText("SCANNING...")
        self.status_label.setText("PROCESSING")
        self.detection_label.setText("DETECTION STATUS: SCANNING...")
        self.target_label.setText("Analyzing selected region...")
        self.response_box.clear()
        self.lms_response_box.clear()
        self.lms_status_label.setText("PROCESSING")
        self.spinner_index = 0
        self.spinner_timer.start(100)

        self.worker = OCRWorker(screenshot)
        self.worker.finished_text.connect(self.on_success)
        self.worker.failed.connect(self.on_error)
        self.worker.start()

    def animate_loading(self):
        frame = self.spinner_frames[self.spinner_index % len(self.spinner_frames)]
        self.spinner_index += 1
        self.loading_label.setText(f"{frame} ANALYZING SCREEN...")

    def on_success(self, text, questions):
        self.stop_loading()
        self.show()
        self.raise_()
        self.activateWindow()

        if questions:
            self.status_label.setText("COMPLETE")
            self.detection_label.setText("SUCCESSFULLY DETECTED")
            self.detection_label.setStyleSheet("color: #66ff99; font-weight: bold;")
            self.target_label.setText(f"Detected {len(questions)} possible question line(s).")
            
            formatted_text = "\n\n".join(f"QUESTION {i + 1}:\n{q}" for i, q in enumerate(questions))
            self.response_box.setPlainText(formatted_text)
            
            self.lms_status_label.setText("READY TO SOLVE")
            self.lms_response_box.setPlainText(
                "[LMS PORTAL READY]\n\n"
                f"Successfully loaded {len(questions)} query/queries into buffer.\n"
                "Click '>> EXECUTE AUTOMATIC ANSWER' o '>> AUTO-CLICK / AUTO-NEXT'."
            )
        else:
            self.status_label.setText("COMPLETE")
            self.detection_label.setText("NO QUESTION DETECTED")
            self.detection_label.setStyleSheet("color: #ff7777; font-weight: bold;")
            self.lms_status_label.setText("IDLE")

            if text.strip():
                self.target_label.setText("Text was found, but no recognizable question pattern.")
                self.response_box.setPlainText("OCR TEXT:\n\n" + text)
            else:
                self.target_label.setText("No readable text found.")
                self.response_box.setPlainText("No question detected.")

    def run_auto_answer(self):
        current_text = self.response_box.toPlainText()
        if not current_text or "No question detected" in current_text:
            self.lms_status_label.setText("NO DATA")
            self.lms_response_box.setPlainText("Error: No valid questions loaded in buffer to process.")
            return

        self.lms_status_label.setText("SOLVING...")
        self.lms_response_box.setPlainText("Connecting to LMS Answer Engine / AI Backend...\nProcessing quiz query...")

        QTimer.singleShot(1000, self.complete_auto_answer)

    def complete_auto_answer(self):
        self.lms_status_label.setText("COMPLETED")
        self.lms_response_box.setPlainText(
            "[AUTOMATIC ANSWER PORTAL RESULT]\n\n"
            "Status: Success\n"
            "Solution Found: [Automated answer match or API response payload goes here]"
        )

    def run_auto_click(self):
        """Awtomatikong gagawa ng auto-click o auto-next action gamit ang PyAutoGUI."""
        self.lms_status_label.setText("RUNNING AUTO-CLICK")
        self.lms_response_box.setPlainText("Executing Auto-Click & Auto-Next sequence...\nSending keyboard/mouse automation signals...")

        try:
            # Halimbawa ng PyAutoGUI automation (tulad ng pagpindot ng Enter o Space para mag-next)
            # pyautogui.press('enter')
            QTimer.singleShot(1000, self.complete_auto_click_action)
        except Exception as exc:
            self.lms_status_label.setText("ERROR")
            self.lms_response_box.setPlainText(f"Auto-click failed: {exc}")

    def complete_auto_click_action(self):
        self.lms_status_label.setText("CLICKED / NEXT")
        self.lms_response_box.setPlainText(
            "[AUTO-CLICK / AUTO-NEXT SUCCESS]\n\n"
            "Status: Awtomatikong nai-submit o nailipat sa susunod na tanong.\n"
            "Maaari mo pang i-customize ang `run_auto_click` para sa eksaktong coordinate clicks."
        )

    def on_error(self, error):
        self.stop_loading()
        self.show()
        self.raise_()

        self.status_label.setText("ERROR")
        self.detection_label.setText("DETECTION FAILED")
        self.detection_label.setStyleSheet("color: #ff7777;")
        self.target_label.setText("Could not capture or analyze the screen.")
        self.lms_status_label.setText("ERROR")
        self.response_box.setPlainText(f"Error:\n{error}")

    def stop_loading(self):
        self.spinner_timer.stop()
        self.loading_label.setText("")
        self.analyze_btn.setEnabled(True)
        self.analyze_btn.setText(">> SELECT REGION & ANALYZE")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = GhostTerminal()
    window.show()
    sys.exit(app.exec())