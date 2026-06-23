import argparse
import sys
import time
import threading
import keyboard
from typing import Optional, Tuple

from solver import Solver
from screen_reader import ScreenReader
from input_emulator import InputEmulator


def print_banner() -> None:
    print("=" * 60)
    print("  HOT OR COLD: GUESS THE WORD - BLITZ EDITION")
    print("=" * 60)
    print("  [F7] Toggle Bot Start/Stop")
    print("  [Ctrl+C] Exit Program")
    print("=" * 60)
    print()


def get_spam_list() -> list[str]:
    categories = {
        "animals": ["dog", "cat", "bird", "fish", "lion", "tiger", "bear", "elephant", "monkey", "horse", "cow", "pig", "sheep", "chicken", "duck", "rabbit", "mouse", "rat", "deer", "wolf", "fox", "zebra", "giraffe", "hippo", "rhino", "whale", "dolphin", "shark", "octopus", "crab", "snail", "bee", "ant", "spider", "fly", "butterfly", "worm", "snake", "lizard", "turtle", "frog"],
        "space": ["sun", "moon", "star", "planet", "mars", "jupiter", "saturn", "venus", "earth", "mercury", "uranus", "neptune", "pluto", "sky", "universe", "galaxy", "comet", "asteroid", "rocket", "astronaut", "alien", "blackhole", "orbit", "telescope"],
        "body": ["head", "eye", "nose", "ear", "mouth", "lip", "tooth", "tongue", "neck", "shoulder", "arm", "elbow", "wrist", "hand", "finger", "thumb", "chest", "stomach", "back", "hip", "leg", "knee", "ankle", "foot", "toe", "skin", "bone", "blood", "heart", "brain", "lung"],
        "utensils_items": ["fork", "spoon", "knife", "plate", "bowl", "cup", "glass", "mug", "pot", "pan", "tray", "key", "phone", "book", "pen", "pencil", "eraser", "ruler", "chair", "table", "desk", "lamp", "bed", "clock", "mirror", "brush", "comb", "soap", "towel", "pillow", "blanket", "door", "window", "wall", "floor", "roof"],
        "emotions": ["happy", "sad", "angry", "scared", "excited", "bored", "tired", "love", "hate", "surprised", "proud", "shy", "calm", "nervous", "lonely", "silly", "brave"],
        "nature": ["tree", "flower", "leaf", "grass", "rock", "stone", "sand", "dirt", "mountain", "hill", "valley", "river", "lake", "ocean", "sea", "beach", "island", "cloud", "rain", "snow", "wind", "storm", "fire", "ice", "water", "gold", "silver", "diamond"],
        "food": ["apple", "banana", "orange", "grape", "strawberry", "pear", "peach", "melon", "lemon", "lime", "bread", "cheese", "milk", "egg", "butter", "honey", "sugar", "salt", "pepper", "rice", "pasta", "pizza", "burger", "taco", "candy", "cake", "cookie", "chocolate", "icecream", "donut", "juice", "water", "tea", "coffee"],
        "colors": ["red", "blue", "green", "yellow", "orange", "purple", "pink", "brown", "black", "white", "grey", "gold", "silver"],
        "misc": ["ball", "toy", "game", "card", "box", "bag", "hat", "shirt", "pants", "shoe", "sock", "coat", "dress", "belt", "watch", "ring", "money", "coin", "bill", "ticket", "map", "flag", "bell", "drum", "piano", "guitar", "flute"]
    }
    all_words = []
    for cat in categories.values():
        all_words.extend(cat)
    return all_words


def run_spam_bot(args: argparse.Namespace) -> None:
    print_banner()
    
    emulator = InputEmulator(typing_delay=0.01)
    word_list = get_spam_list()
    bot_running = False

    def toggle():
        nonlocal bot_running
        bot_running = not bot_running
        print(f"\n>>> Bot {'STARTED' if bot_running else 'STOPPED'}")

    keyboard.add_hotkey("f7", toggle)

    if args.region:
        parts = [int(x) for x in args.region.split(",")]
        emulator.set_game_region(tuple(parts))
    else:
        from screen_reader import ScreenReader
        reader = ScreenReader()
        region = reader.find_roblox_window()
        if region:
            emulator.set_game_region(region)

    print("\nReady! Press F7 to start/stop the spammer.")
    
    idx = 0
    try:
        while True:
            if not bot_running:
                time.sleep(0.1)
                continue

            word = word_list[idx % len(word_list)]
            print(f"  Spamming: {word} ({idx+1})")
            emulator.send_guess(word)
            idx += 1
            time.sleep(0.05)
    except KeyboardInterrupt:
        print("\nBot exited.")


def run_auto_bot(args: argparse.Namespace) -> None:
    print_banner()
    solver = Solver()
    reader = ScreenReader()
    emulator = InputEmulator(typing_delay=args.typing_delay)
    bot_running = False

    def toggle():
        nonlocal bot_running
        bot_running = not bot_running
        print(f"\n>>> Bot {'STARTED' if bot_running else 'STOPPED'}")

    keyboard.add_hotkey("f7", toggle)

    if args.region:
        parts = [int(x) for x in args.region.split(",")]
        emulator.set_game_region(tuple(parts))
    else:
        region = reader.find_roblox_window()
        if region:
            emulator.set_game_region(region)

    print("\nReady! Press F7 to start/stop the bot.")
    
    guess_count = 0
    try:
        while guess_count < args.max_guesses:
            if not bot_running:
                time.sleep(0.1)
                continue

            next_word = solver.next_guess()
            if next_word is None: break

            guess_count += 1
            print(f"  [{guess_count}] Guessing: '{next_word}' | {solver.get_status()}")
            emulator.send_guess(next_word)

            result = None
            start_wait = time.time()
            while time.time() - start_wait < args.wait_timeout:
                if not bot_running: break
                found = reader.read_guesses_from_game()
                for g in found:
                    if g.word == next_word:
                        result = g
                        break
                if result: break
                time.sleep(0.05)

            if result:
                rank = result.rank
                phase = solver.process_feedback(next_word, rank)
                print(f"      Result: #{rank} -> Phase: {phase}")
                if rank == 1:
                    print(f"\n{'='*20}\nSOLVED! Word: {next_word}\n{'='*20}")
                    bot_running = False
                    break
            else:
                print(f"      No result found for '{next_word}', skipping...")

    except KeyboardInterrupt:
        print("\nBot exited.")


def run_interactive(args: argparse.Namespace) -> None:
    print_banner()
    solver = Solver()
    print("Interactive Mode: Enter '<word> <rank>' or 'next' for suggestions.")
    while True:
        try:
            line = input(">>> ").strip()
            if line.lower() == "quit": break
            if line.lower() == "next":
                w = solver.next_guess()
                print(f"  Suggested: {w}" if w else "  No more words.")
                continue
            parts = line.split()
            if len(parts) == 2:
                word, rank = parts[0].lower(), int(parts[1])
                phase = solver.process_feedback(word, rank)
                print(f"  Recorded: {word} -> #{rank} | {solver.get_status()}")
                if rank == 1: break
        except (EOFError, KeyboardInterrupt): break


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["auto", "interactive", "build", "spam"], default="interactive")
    parser.add_argument("--region", type=str, default=None)
    parser.add_argument("--max-guesses", type=int, default=200)
    parser.add_argument("--wait-timeout", type=float, default=30.0)
    parser.add_argument("--poll-interval", type=float, default=0.5)
    parser.add_argument("--typing-delay", type=float, default=0.03)
    args = parser.parse_args()

    if args.mode == "build":
        from build_index import main as b_main
        b_main()
    elif args.mode == "spam":
        run_spam_bot(args)
    elif args.mode == "auto":
        run_auto_bot(args)
    else:
        run_interactive(args)


if __name__ == "__main__":
    main()
