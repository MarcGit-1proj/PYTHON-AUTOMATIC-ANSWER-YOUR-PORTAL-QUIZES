
import sys
import os
import re

import pyautogui
import pytesseract

from PySide6.QtCore import Qt, QThread, Signal, QTimer
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QApplication,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QFrame,
    QTextEdit,
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

    # Clean up OCR output line by line.
    lines = [
        re.sub(r"\s+", " ", line).strip(" \t|")
        for line in text.splitlines()
    ]

    for line in lines:
        if len(line) < 5:
            continue

        normalized = line.lower()

        # Skip likely interface labels and application controls.
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
        ]

        if any(label in normalized for label in ignored):
            continue

        # Strong signal: a question mark.
        has_question_mark = "?" in line

        # Recognize common question/instruction wording.
        has_question_pattern = any(
            re.search(pattern, normalized)
            for pattern in QUESTION_PATTERNS
        )

        if has_question_mark or has_question_pattern:
            # Avoid displaying duplicate lines.
            key = normalized
            if key not in seen:
                seen.add(key)
                found.append(line)

    return found


class OCRWorker(QThread):
    finished_text = Signal(str, list)
    failed = Signal(str)

    def run(self):
        try:
            if os.path.isfile(TESSERACT_PATH):
                pytesseract.pytesseract.tesseract_cmd = TESSERACT_PATH

            # Capture the screen behind the floating window.
            screenshot = pyautogui.screenshot()

            # Read visible text.
            text = pytesseract.image_to_string(
                screenshot,
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
        self.drag_position = None

        self.setWindowTitle("GHOST TERMINAL")
        self.resize(440, 540)

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

        status_row = QHBoxLayout()
        status_row.addWidget(QLabel("SYSTEM STATUS"))
        status_row.addStretch()

        self.status_label = QLabel("READY")
        self.status_label.setObjectName("muted")
        status_row.addWidget(self.status_label)

        root.addLayout(status_row)

        root.addWidget(QLabel("TARGET MONITOR"))

        self.target_label = QLabel(
            "Ready to detect a question on screen."
        )
        self.target_label.setWordWrap(True)
        root.addWidget(self.target_label)

        self.analyze_btn = QPushButton(">> ANALYZE TARGET")
        self.analyze_btn.clicked.connect(self.start_analysis)
        root.addWidget(self.analyze_btn)

        self.loading_label = QLabel("")
        self.loading_label.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )
        self.loading_label.setFont(QFont("Consolas", 12))
        root.addWidget(self.loading_label)

        self.detection_label = QLabel("DETECTION STATUS: READY")
        self.detection_label.setWordWrap(True)
        root.addWidget(self.detection_label)

        root.addWidget(QLabel("DETECTED QUESTION / OCR TEXT"))

        self.response_box = QTextEdit()
        self.response_box.setReadOnly(True)
        self.response_box.setPlaceholderText(
            "Detected question will appear here..."
        )
        root.addWidget(self.response_box, 1)

        footer = QLabel("SCREEN OCR // QUESTION DETECTION")
        footer.setObjectName("muted")
        footer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.addWidget(footer)

        self.spinner_frames = ["|", "/", "-", "\\"]
        self.spinner_index = 0

        self.spinner_timer = QTimer(self)
        self.spinner_timer.timeout.connect(self.animate_loading)

    def start_analysis(self):
        if self.worker is not None and self.worker.isRunning():
            return

        if os.path.isfile(TESSERACT_PATH):
            pytesseract.pytesseract.tesseract_cmd = TESSERACT_PATH

        self.analyze_btn.setEnabled(False)
        self.analyze_btn.setText("SCANNING...")
        self.status_label.setText("PROCESSING")
        self.detection_label.setText("DETECTION STATUS: SCANNING...")
        self.target_label.setText(
            "Preparing screen capture..."
        )
        self.response_box.clear()
        self.spinner_index = 0

        self.spinner_timer.start(100)

        # Hide this window so its own labels are not read as questions.
        self.hide()

        # Allow the desktop to redraw before taking the screenshot.
        QTimer.singleShot(350, self.launch_ocr_worker)

    def launch_ocr_worker(self):
        self.worker = OCRWorker()
        self.worker.finished_text.connect(self.on_success)
        self.worker.failed.connect(self.on_error)
        self.worker.start()

    def animate_loading(self):
        frame = self.spinner_frames[
            self.spinner_index % len(self.spinner_frames)
        ]
        self.spinner_index += 1
        self.loading_label.setText(
            f"{frame} ANALYZING SCREEN..."
        )

    def on_success(self, text, questions):
        self.stop_loading()
        self.show()
        self.raise_()
        self.activateWindow()

        if questions:
            self.status_label.setText("COMPLETE")
            self.detection_label.setText(
                "SUCCESSFULLY DETECTED"
            )
            self.detection_label.setStyleSheet(
                "color: #66ff99; font-weight: bold;"
            )
            self.target_label.setText(
                f"Detected {len(questions)} possible question line(s)."
            )
            self.response_box.setPlainText(
                "\n\n".join(
                    f"QUESTION {i + 1}:\n{question}"
                    for i, question in enumerate(questions)
                )
            )
        else:
            self.status_label.setText("COMPLETE")
            self.detection_label.setText("NO QUESTION DETECTED")
            self.detection_label.setStyleSheet(
                "color: #ff7777; font-weight: bold;"
            )

            if text.strip():
                self.target_label.setText(
                    "Text was found, but no recognizable question pattern."
                )
                self.response_box.setPlainText(
                    "No question detected.\n\n"
                    "Some screen text was readable, but it did not match "
                    "the current question patterns.\n\n"
                    "OCR TEXT FOR CHECKING:\n\n" + text
                )
            else:
                self.target_label.setText(
                    "No readable text found on the captured screen."
                )
                self.response_box.setPlainText(
                    "NO QUESTION DETECTED\n\n"
                    "Try making the question larger and clearer."
                )

    def on_error(self, error):
        self.stop_loading()
        self.show()
        self.raise_()

        self.status_label.setText("ERROR")
        self.detection_label.setText("DETECTION FAILED")
        self.detection_label.setStyleSheet("color: #ff7777;")
        self.target_label.setText(
            "Could not capture or analyze the screen."
        )
        self.response_box.setPlainText(
            f"Error:\n{error}\n\n"
            "Check that Tesseract OCR is installed and that "
            "the required Python packages are available."
        )

    def stop_loading(self):
        self.spinner_timer.stop()
        self.loading_label.setText("")
        self.analyze_btn.setEnabled(True)
        self.analyze_btn.setText(">> ANALYZE TARGET")

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_position = (
                event.globalPosition().toPoint()
                - self.frameGeometry().topLeft()
            )
            event.accept()

    def mouseMoveEvent(self, event):
        if (
            self.drag_position is not None
            and event.buttons() & Qt.MouseButton.LeftButton
        ):
            self.move(
                event.globalPosition().toPoint()
                - self.drag_position
            )
            event.accept()

    def mouseReleaseEvent(self, event):
        self.drag_position = None
        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)

    window = GhostTerminal()
    window.show()

    sys.exit(app.exec())
