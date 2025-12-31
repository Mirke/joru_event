import sys
import json
import re
from pathlib import Path
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget,
    QVBoxLayout, QHBoxLayout,
    QListWidget, QListWidgetItem,
    QTextEdit, QPushButton,
    QFileDialog, QLabel, QCheckBox,
    QComboBox, QLineEdit
)
from PyQt6.QtGui import QColor


class ChatWordViewer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Chat Word Viewer")
        self.setMinimumSize(1000, 600)

        self.comments = []
        self.word_index = {}     # word -> list[(user, msg)]
        self.word_counts = {}   # word -> int

        self.nouns = set()
        self.adjectives = set()
        self.blacklist = set()
        self.saved_words = set()

        self.load_pos_files()
        self.load_blacklist()
        self.load_saved_words()
        self.build_ui()

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
        base = Path(__file__).parent
        path = base / "blacklist.txt"

        if not path.exists():
            self.blacklist = set()
            return

        self.blacklist = {
            line.strip().lower()
            for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        }

    def load_saved_words(self):
        base = Path(__file__).parent
        path = base / "saved_words.txt"

        if not path.exists():
            self.saved_words = set()
            return

        self.saved_words = {
            line.strip().lower()
            for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        }

    def save_word(self, word):
        if word in self.saved_words:
            return

        self.saved_words.add(word)
        path = Path(__file__).parent / "saved_words.txt"
        with path.open("a", encoding="utf-8") as f:
            f.write(word + "\n")

    # ---------------- UI ----------------
    def build_ui(self):
        root = QWidget()
        self.setCentralWidget(root)

        layout = QVBoxLayout(root)

        # ===== HEADER =====
        header = QHBoxLayout()

        title = QLabel("Chat Word Viewer")
        title.setStyleSheet("font-size: 20px; font-weight: bold;")

        load_btn = QPushButton("Load JSON")
        load_btn.clicked.connect(self.open_json)

        self.noun_cb = QCheckBox("Nouns")
        self.adj_cb = QCheckBox("Adjectives")

        for cb in (self.noun_cb, self.adj_cb):
            cb.stateChanged.connect(self.populate_word_list)

        self.sort_box = QComboBox()
        self.sort_box.addItems(["Alphabetical", "By count"])
        self.sort_box.currentIndexChanged.connect(self.populate_word_list)

        header.addWidget(title)
        header.addStretch()
        header.addWidget(load_btn)
        header.addWidget(self.noun_cb)
        header.addWidget(self.adj_cb)
        header.addWidget(QLabel("Sort:"))
        header.addWidget(self.sort_box)

        layout.addLayout(header)

        # ===== SEARCH =====
        self.search = QLineEdit()
        self.search.setPlaceholderText("Search words...")
        self.search.textChanged.connect(self.populate_word_list)
        layout.addWidget(self.search)

        # ===== MAIN =====
        main = QHBoxLayout()
        layout.addLayout(main)

        self.word_list = QListWidget()
        self.word_list.itemSelectionChanged.connect(self.word_selected)
        self.word_list.itemDoubleClicked.connect(self.word_double_clicked)
        main.addWidget(self.word_list, 1)

        self.messages = QTextEdit()
        self.messages.setReadOnly(True)
        main.addWidget(self.messages, 3)

    # ---------------- JSON loading ----------------
    def open_json(self):
        file, _ = QFileDialog.getOpenFileName(
            self,
            "Open Twitch Chat JSON",
            "",
            "JSON Files (*.json)"
        )
        if file:
            self.load_json(file)

    def load_json(self, path):
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.comments = data.get("comments", [])
        self.build_word_index()
        self.populate_word_list()

    # ---------------- Word processing ----------------
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
        filters = []

        if self.noun_cb.isChecked():
            filters.append(word in self.nouns)
        if self.adj_cb.isChecked():
            filters.append(word in self.adjectives)

        return not filters or any(filters)

    def populate_word_list(self):
        self.word_list.clear()
        query = self.search.text().lower()

        words = [
            w for w in self.word_index.keys()
            if self.word_matches_pos(w)
            and (not query or query in w)
        ]

        if self.sort_box.currentText() == "By count":
            words.sort(key=lambda w: self.word_counts.get(w, 0), reverse=True)
        else:
            words.sort()

        for w in words:
            count = self.word_counts[w]
            item = QListWidgetItem(f"{w} ({count})")

            if w in self.saved_words:
                item.setForeground(QColor("#3aa655"))  # green

            self.word_list.addItem(item)

    # ---------------- Selection ----------------
    def word_selected(self):
        item = self.word_list.currentItem()
        if not item:
            return

        word = item.text().rsplit(" (", 1)[0]
        entries = self.word_index.get(word, [])

        self.messages.clear()
        for user, msg in entries:
            self.messages.append(
                f"<b>{user}</b>: {msg}<br>"
            )

    def word_double_clicked(self, item):
        word = item.text().rsplit(" (", 1)[0]
        self.save_word(word)
        item.setForeground(QColor("#3aa655"))


# ---------------- Run ----------------
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ChatWordViewer()
    window.show()
    app.exec()
