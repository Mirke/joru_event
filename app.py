import sys
import json
import re
from pathlib import Path

# ==========================================================
# ======================= CONFIG ===========================
# ==========================================================

APP_TITLE = "Chat Word Viewer"
WINDOW_MIN_SIZE = (1000, 600)

NAV_OVERLAY_BG = "black"
NAV_OVERLAY_COLOR = "white"
NAV_OVERLAY_FONT_SIZE = 10
NAV_OVERLAY_PADDING = 3
NAV_OVERLAY_OFFSET_X = -18
NAV_OVERLAY_OFFSET_Y = 0

SAVED_WORD_COLOR = "#3aa655"
DEFAULT_WORD_COLOR = "black"

CAPS_DOUBLE_TAP_MS = 350

HEADER_FONT_SIZE = 20

# ==========================================================
# ==========================================================

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QDialog,
    QVBoxLayout, QHBoxLayout,
    QListWidget, QListWidgetItem,
    QTextEdit, QPushButton,
    QFileDialog, QLabel, QCheckBox,
    QComboBox, QLineEdit
)
from PyQt6.QtGui import QColor
from PyQt6.QtCore import Qt, QEvent, QTimer


# ================= Saved Words Window =====================

class SavedWordsDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.setWindowTitle("Saved Words")
        self.setMinimumSize(300, 400)

        layout = QVBoxLayout(self)

        self.list = QListWidget()
        layout.addWidget(self.list)

        self.input = QLineEdit()
        self.input.setPlaceholderText("Add word…")
        layout.addWidget(self.input)

        btns = QHBoxLayout()
        add_btn = QPushButton("Add")
        remove_btn = QPushButton("Remove selected")

        add_btn.clicked.connect(self.add_word)
        remove_btn.clicked.connect(self.remove_word)

        btns.addWidget(add_btn)
        btns.addWidget(remove_btn)
        layout.addLayout(btns)

        self.refresh()

    def refresh(self):
        self.list.clear()
        for w in sorted(self.parent.saved_words):
            self.list.addItem(w)

    def add_word(self):
        word = self.input.text().strip().lower()
        if not word:
            return
        self.parent.saved_words.add(word)
        self.parent.save_words_to_file()
        self.parent.populate_word_list()
        self.input.clear()
        self.refresh()

    def remove_word(self):
        item = self.list.currentItem()
        if not item:
            return
        word = item.text()
        self.parent.saved_words.discard(word)
        self.parent.save_words_to_file()
        self.parent.populate_word_list()
        self.refresh()


# =================== Main Window ===========================

class ChatWordViewer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP_TITLE)
        self.setMinimumSize(*WINDOW_MIN_SIZE)

        self.comments = []
        self.word_index = {}
        self.word_counts = {}

        self.nouns = set()
        self.adjectives = set()
        self.blacklist = set()
        self.saved_words = set()

        # Navigation / quick select
        self.nav_labels = {}
        self.awaiting_nav_input = False

        self.caps_count = 0
        self.caps_timer = QTimer()
        self.caps_timer.setSingleShot(True)
        self.caps_timer.timeout.connect(self.reset_caps)

        self.load_pos_files()
        self.load_blacklist()
        self.load_saved_words()
        self.build_ui()

        self.installEventFilter(self)

    # ---------------- File loading ----------------

    def load_pos_files(self):
        base = Path(__file__).parent

        def load_txt(name):
            path = base / name
            if not path.exists():
                return set()
            return {
                line.strip().lower()
                for line in path.read_text(encoding="utf-8").splitlines()
                if line.strip()
            }

        self.nouns = load_txt("nouns.txt")
        self.adjectives = load_txt("adjectives.txt")

    def load_blacklist(self):
        path = Path(__file__).parent / "blacklist.txt"
        if path.exists():
            self.blacklist = {
                line.strip().lower()
                for line in path.read_text(encoding="utf-8").splitlines()
                if line.strip()
            }

    def load_saved_words(self):
        path = Path(__file__).parent / "saved_words.txt"
        if path.exists():
            self.saved_words = {
                line.strip().lower()
                for line in path.read_text(encoding="utf-8").splitlines()
                if line.strip()
            }

    def save_words_to_file(self):
        path = Path(__file__).parent / "saved_words.txt"
        path.write_text("\n".join(sorted(self.saved_words)), encoding="utf-8")

    # ---------------- UI ----------------

    def build_ui(self):
        root = QWidget()
        self.setCentralWidget(root)
        layout = QVBoxLayout(root)

        header = QHBoxLayout()

        title = QLabel(APP_TITLE)
        title.setStyleSheet(
            f"font-size:{HEADER_FONT_SIZE}px;font-weight:bold;"
        )

        self.load_btn = QPushButton("Load JSON")
        self.load_btn.clicked.connect(self.open_json)

        self.saved_btn = QPushButton("Saved Words")
        self.saved_btn.clicked.connect(self.open_saved_words)

        self.noun_cb = QCheckBox("Nouns")
        self.adj_cb = QCheckBox("Adjectives")
        self.hide_user_cb = QCheckBox("&Hide usernames")
        self.hide_user_cb.stateChanged.connect(self.word_selected)

        for cb in (self.noun_cb, self.adj_cb):
            cb.stateChanged.connect(self.populate_word_list)

        self.sort_box = QComboBox()
        self.sort_box.addItems(["Alphabetical", "By count"])
        self.sort_box.currentIndexChanged.connect(self.populate_word_list)

        header.addWidget(title)
        header.addStretch()
        header.addWidget(self.load_btn)
        header.addWidget(self.saved_btn)
        header.addWidget(self.noun_cb)
        header.addWidget(self.adj_cb)
        header.addWidget(self.hide_user_cb)
        header.addWidget(QLabel("Sort:"))
        header.addWidget(self.sort_box)

        layout.addLayout(header)

        self.search = QLineEdit()
        self.search.setPlaceholderText("Search words…")
        self.search.textChanged.connect(self.populate_word_list)
        layout.addWidget(self.search)

        main = QHBoxLayout()
        layout.addLayout(main)

        self.word_list = QListWidget()
        self.word_list.itemSelectionChanged.connect(self.word_selected)
        self.word_list.itemDoubleClicked.connect(self.word_double_clicked)
        main.addWidget(self.word_list, 1)

        self.messages = QTextEdit()
        self.messages.setReadOnly(True)
        main.addWidget(self.messages, 3)

        self.nav_targets = [
            self.load_btn,
            self.saved_btn,
            self.noun_cb,
            self.adj_cb,
            self.sort_box,
            self.search,
            self.word_list,
            self.messages,
        ]

    # ---------------- JSON ----------------

    def open_json(self):
        file, _ = QFileDialog.getOpenFileName(
            self, "Open Twitch Chat JSON", "", "JSON Files (*.json)"
        )
        if file:
            with open(file, "r", encoding="utf-8") as f:
                data = json.load(f)

            self.comments = data.get("comments", [])
            self.build_word_index()
            self.populate_word_list()

    # ---------------- Processing ----------------

    def build_word_index(self):
        self.word_index.clear()
        self.word_counts.clear()

        for c in self.comments:
            user = c.get("commenter", {}).get("display_name", "Unknown")
            if user.lower() in self.blacklist:
                continue

            msg = c.get("message", {}).get("body", "")
            words = re.findall(r"\b\w+\b", msg.lower())

            for w in words:
                self.word_index.setdefault(w, []).append((user, msg))
                self.word_counts[w] = self.word_counts.get(w, 0) + 1

    def word_matches_pos(self, word):
        active = []
        if self.noun_cb.isChecked():
            active.append(word in self.nouns)
        if self.adj_cb.isChecked():
            active.append(word in self.adjectives)
        return not active or any(active)

    def populate_word_list(self):
        self.word_list.clear()
        q = self.search.text().lower()

        words = [
            w for w in self.word_index
            if self.word_matches_pos(w) and (not q or q in w)
        ]

        if self.sort_box.currentText() == "By count":
            words.sort(key=lambda w: self.word_counts[w], reverse=True)
        else:
            words.sort()

        for w in words:
            item = QListWidgetItem(f"{w} ({self.word_counts[w]})")
            if w in self.saved_words:
                item.setForeground(QColor(SAVED_WORD_COLOR))
            self.word_list.addItem(item)

    # ---------------- Selection ----------------

    def word_selected(self):
        item = self.word_list.currentItem()
        if not item:
            return

        word = item.text().rsplit(" (", 1)[0]
        self.messages.clear()

        for user, msg in self.word_index.get(word, []):
            if self.hide_user_cb.isChecked():
                self.messages.append(msg)
            else:
                self.messages.append(f"<b>{user}</b>: {msg}")

    def word_double_clicked(self, item):
        word = item.text().rsplit(" (", 1)[0]

        if word in self.saved_words:
            self.saved_words.remove(word)
            item.setForeground(QColor(DEFAULT_WORD_COLOR))
        else:
            self.saved_words.add(word)
            item.setForeground(QColor(SAVED_WORD_COLOR))

        self.save_words_to_file()

    def open_saved_words(self):
        SavedWordsDialog(self).exec()

    # ---------------- Quick Select ----------------

    def reset_caps(self):
        self.caps_count = 0

    def clear_selection(self):
        self.word_list.clearSelection()
        self.search.clear()
        self.messages.clear()
        self.setFocus()

    def show_nav_overlays(self):
        self.clear_nav_overlays()

        for i, widget in enumerate(self.nav_targets):
            label = QLabel(str(i), self)
            label.setStyleSheet(
                f"background:{NAV_OVERLAY_BG};"
                f"color:{NAV_OVERLAY_COLOR};"
                f"padding:{NAV_OVERLAY_PADDING}px;"
                f"font-size:{NAV_OVERLAY_FONT_SIZE}px;"
            )
            pos = widget.mapTo(self, widget.rect().topLeft())
            label.move(
                pos.x() + NAV_OVERLAY_OFFSET_X,
                pos.y() + NAV_OVERLAY_OFFSET_Y
            )
            label.show()
            self.nav_labels[i] = label

    def clear_nav_overlays(self):
        for lbl in self.nav_labels.values():
            lbl.deleteLater()
        self.nav_labels.clear()

    def eventFilter(self, obj, event):
        if event.type() == QEvent.Type.KeyPress:

            # ---- CAPS DOUBLE TAP ----
            if event.key() == Qt.Key.Key_CapsLock:
                self.caps_count += 1
                if self.caps_count == 1:
                    self.caps_timer.start(CAPS_DOUBLE_TAP_MS)
                elif self.caps_count == 2:
                    self.caps_timer.stop()
                    self.caps_count = 0
                    self.clear_selection()
                    self.show_nav_overlays()
                    self.awaiting_nav_input = True
                return True

            # ---- WAITING FOR NUMBER ----
            if self.awaiting_nav_input:
                self.clear_nav_overlays()
                self.awaiting_nav_input = False

                if Qt.Key.Key_0 <= event.key() <= Qt.Key.Key_9:
                    idx = event.key() - Qt.Key.Key_0
                    if idx < len(self.nav_targets):
                        self.nav_targets[idx].setFocus()
                return True

            # ---- ESC ----
            if event.key() == Qt.Key.Key_Escape:
                self.clear_selection()
                self.clear_nav_overlays()
                self.awaiting_nav_input = False
                return True

        return super().eventFilter(obj, event)


# ---------------- Run ----------------

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ChatWordViewer()
    window.show()
    app.exec()
