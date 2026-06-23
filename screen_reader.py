from __future__ import annotations

import re
import time
from dataclasses import dataclass
from typing import List, Optional, Tuple

import numpy as np
import pyautogui
import easyocr
from PIL import Image

try:
    import mss
    HAS_MSS = True
except ImportError:
    HAS_MSS = False


@dataclass
class GuessLine:
    word: str
    rank: int


class ScreenReader:
    def __init__(self) -> None:
        print("  Initializing EasyOCR (first run downloads model ~100MB)...")
        self.reader = easyocr.Reader(["en"], gpu=False)
        self.sct = mss.mss() if HAS_MSS else None
        self.guess_history: List[GuessLine] = []
        self.last_rank_count = 0

    def capture_screen(self, region: Optional[Tuple[int, int, int, int]] = None) -> Image.Image:
        if self.sct:
            if region:
                monitor = {"left": region[0], "top": region[1],
                           "width": region[2], "height": region[3]}
            else:
                monitor = self.sct.monitors[1]
            screenshot = self.sct.grab(monitor)
            img = Image.frombytes("RGB", screenshot.size, screenshot.bgra, "raw", "BGRX")
            return img
        else:
            if region:
                return pyautogui.screenshot(region=region)
            return pyautogui.screenshot()

    def capture_region(self, left: int, top: int, width: int, height: int) -> Image.Image:
        if self.sct:
            monitor = {"left": left, "top": top, "width": width, "height": height}
            screenshot = self.sct.grab(monitor)
            return Image.frombytes("RGB", screenshot.size, screenshot.bgra, "raw", "BGRX")
        return pyautogui.screenshot(region=(left, top, width, height))

    def extract_text(self, img: Image.Image) -> str:
        img_np = np.array(img)
        results = self.reader.readtext(img_np, detail=0)
        return " ".join(results)

    def parse_guess_lines(self, text: str) -> List[GuessLine]:
        results = []
        for match in re.finditer(r"([a-zA-Z]+)\s*(?:x\d+)?\s*#(\d+)", text):
            word = match.group(1).lower()
            rank = int(match.group(2))
            results.append(GuessLine(word=word, rank=rank))
        return results

    def find_roblox_window(self) -> Optional[Tuple[int, int, int, int]]:
        try:
            import pygetwindow as gw
            windows = gw.getWindowsWithTitle("Roblox")
            if windows:
                win = windows[0]
                return (win.left, win.top, win.width, win.height)
        except ImportError:
            pass
        return None

    def read_guesses_from_game(
        self, game_region: Optional[Tuple[int, int, int, int]] = None
    ) -> List[GuessLine]:
        if game_region is None:
            game_region = self.find_roblox_window()

        if game_region:
            # CROP: Focus on the right half of the window where ranks are displayed
            # This makes OCR 3-4x faster
            left, top, width, height = game_region
            crop_left = left + int(width * 0.4)
            img = self.capture_region(crop_left, top, width - (crop_left - left), height)
        else:
            img = self.capture_screen()

        text = self.extract_text(img)
        guesses = self.parse_guess_lines(text)
        return guesses

    def get_new_guesses(
        self, game_region: Optional[Tuple[int, int, int, int]] = None
    ) -> List[GuessLine]:
        guesses = self.read_guesses_from_game(game_region)
        new_guesses = []

        existing = {(g.word, g.rank) for g in self.guess_history}

        for g in guesses:
            if (g.word, g.rank) not in existing:
                new_guesses.append(g)
                self.guess_history.append(g)

        return new_guesses

    def wait_for_new_result(
        self,
        timeout: float = 30.0,
        poll_interval: float = 1.0,
        game_region: Optional[Tuple[int, int, int, int]] = None,
    ) -> Optional[GuessLine]:
        start = time.time()

        while time.time() - start < timeout:
            guesses = self.read_guesses_from_game(game_region)
            existing = {(h.word, h.rank) for h in self.guess_history}

            for g in guesses:
                if (g.word, g.rank) not in existing and g.rank != 999999:
                    self.guess_history.append(g)
                    return g

            time.sleep(poll_interval)

        return None

    def find_rank_for_word(
        self, word: str, game_region: Optional[Tuple[int, int, int, int]] = None
    ) -> Optional[int]:
        guesses = self.read_guesses_from_game(game_region)
        for g in guesses:
            if g.word.lower() == word.lower():
                return g.rank
        return None
