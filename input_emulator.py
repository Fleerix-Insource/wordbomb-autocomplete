from __future__ import annotations

import time
from typing import Optional, Tuple

import pyautogui

pyautogui.PAUSE = 0.05
pyautogui.FAILSAFE = True


class InputEmulator:
    def __init__(self, typing_delay: float = 0.03) -> None:
        self.typing_delay = typing_delay
        self.game_region: Optional[Tuple[int, int, int, int]] = None

    def set_game_region(self, region: Tuple[int, int, int, int]) -> None:
        self.game_region = region

    def focus_game(self) -> None:
        if self.game_region:
            cx = self.game_region[0] + self.game_region[2] // 2
            cy = self.game_region[1] + self.game_region[3] // 2
            pyautogui.click(cx, cy)
            time.sleep(0.1)

    def type_word(self, word: str) -> None:
        for char in word:
            pyautogui.press(char)
            time.sleep(self.typing_delay)

    def press_enter(self) -> None:
        pyautogui.press("enter")

    def send_guess(self, word: str) -> None:
        self.focus_game()
        pyautogui.press("/")
        pyautogui.write(word.lower())
        pyautogui.press("enter")

    def send_guess_with_chat(self, word: str) -> None:
        self.focus_game()
        time.sleep(0.1)
        pyautogui.press("/")
        time.sleep(0.1)
        self.type_word(word.lower())
        time.sleep(0.05)
        self.press_enter()
        time.sleep(0.2)

    def click_input_box(self, x: Optional[int] = None, y: Optional[int] = None) -> None:
        if x is not None and y is not None:
            pyautogui.click(x, y)
        elif self.game_region:
            input_x = self.game_region[0] + self.game_region[2] // 2
            input_y = self.game_region[1] + int(self.game_region[3] * 0.3)
            pyautogui.click(input_x, input_y)
        time.sleep(0.1)

    def clear_input(self) -> None:
        pyautogui.hotkey("ctrl", "a")
        time.sleep(0.05)
        pyautogui.press("delete")


class ManualInput:
    def __init__(self) -> None:
        pass

    def send_guess(self, word: str) -> None:
        print(f"  [MANUAL] Please type: {word}")

    def send_guess_with_chat(self, word: str) -> None:
        print(f"  [MANUAL] Please type in chat: /{word}")
