from __future__ import annotations

import json
import os
from pathlib import Path
from typing import List, Tuple

import faiss
import numpy as np

DATA_DIR = Path(__file__).parent / "data"


def ensure_data_dir() -> None:
    DATA_DIR.mkdir(exist_ok=True)


def save_words(words: List[str]) -> None:
    ensure_data_dir()
    with open(DATA_DIR / "words.json", "w") as f:
        json.dump(words, f)


def load_words() -> List[str]:
    with open(DATA_DIR / "words.json", "r") as f:
        return json.load(f)


def save_embeddings(embeddings: np.ndarray) -> None:
    ensure_data_dir()
    np.save(DATA_DIR / "embeddings.npy", embeddings)


def load_embeddings() -> np.ndarray:
    return np.load(DATA_DIR / "embeddings.npy")


def save_faiss_index(index: faiss.Index) -> None:
    ensure_data_dir()
    faiss.write_index(index, str(DATA_DIR / "faiss.index"))


def load_faiss_index() -> faiss.Index:
    return faiss.read_index(str(DATA_DIR / "faiss.index"))


def l2_normalize(embeddings: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
    return embeddings / np.maximum(norms, 1e-12)


def build_faiss_index(embeddings: np.ndarray) -> faiss.Index:
    dim = embeddings.shape[1]
    index = faiss.IndexFlatIP(dim)
    index.add(embeddings)
    return index


def find_rank_and_score(
    sorted_indices: np.ndarray, target_index: int
) -> Tuple[int, float]:
    rank = int(np.where(sorted_indices == target_index)[0][0]) + 1
    return rank, 0.0


def rank_to_color(rank: int) -> str:
    if rank == 1:
        return "#FFD700"
    elif rank <= 100:
        return "#22c55e"
    elif rank <= 1000:
        return "#eab308"
    elif rank <= 5000:
        return "#f97316"
    else:
        return "#ef4444"


def _download_file(url: str, dest: str) -> None:
    import urllib.request
    urllib.request.urlretrieve(url, dest)


def generate_vocabulary(target_size: int = 50_000, min_length: int = 2) -> List[str]:
    """Generate vocabulary from frequency-ranked word lists."""
    words = []
    seen = set()

    sources = [
        "https://raw.githubusercontent.com/first20hours/google-10000-english/master/google-10000-english-usa-no-swears.txt",
        "https://raw.githubusercontent.com/words/an-array-of-english-words/master/words.txt",
    ]

    for url in sources:
        try:
            import tempfile, os
            tmp = os.path.join(tempfile.gettempdir(), "wordlist.txt")
            _download_file(url, tmp)
            with open(tmp, "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    w = line.strip().lower()
                    if w.isalpha() and len(w) >= min_length and w not in seen:
                        words.append(w)
                        seen.add(w)
            print(f"  Loaded {len(words)} words from {url.split('/')[-1]}")
        except Exception as e:
            print(f"  Warning: Could not load {url}: {e}")

    if len(words) < target_size:
        try:
            import nltk
            try:
                nltk.data.find("corpora/words")
            except LookupError:
                nltk.download("words", quiet=True)
            from nltk.corpus import words as nltk_words
            for w in nltk_words.words():
                w = w.strip().lower()
                if w.isalpha() and len(w) >= min_length and w not in seen:
                    words.append(w)
                    seen.add(w)
        except Exception:
            pass

    if len(words) > target_size:
        words = words[:target_size]

    return words
