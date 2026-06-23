from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

from utils import load_faiss_index, load_words, l2_normalize

MODEL_NAME = "all-MiniLM-L6-v2"

SEED_WORDS = [
    "person", "man", "woman", "child", "animal",
    "dog", "cat", "bird", "fish",
    "food", "water", "bread", "fruit", "meat",
    "house", "car", "road", "city", "tree",
    "sun", "moon", "star", "fire", "earth",
    "happy", "sad", "love", "fear", "anger",
    "work", "play", "run", "walk", "talk",
    "red", "blue", "green", "big", "small",
    "time", "year", "day", "night",
    "money", "king", "queen", "book", "hand",
    "good", "bad", "fast", "slow", "hot",
    "cold", "light", "dark", "hard", "soft",
    "music", "game", "play", "sport", "art",
    "school", "store", "park", "shop", "bank",
    "baby", "boy", "girl", "dad", "mom",
    "friend", "teacher", "doctor", "nurse", "police",
    "coffee", "tea", "juice", "milk", "wine",
    "chair", "table", "bed", "door", "wall",
]


@dataclass
class GuessResult:
    word: str
    rank: int


@dataclass
class SolverState:
    guesses: List[GuessResult] = field(default_factory=list)
    best_rank: int = 999999
    best_word: str = ""
    tried_words: Set[str] = field(default_factory=set)
    candidate_pool: List[str] = field(default_factory=list)
    phase: str = "seed"
    guess_count: int = 0


class Solver:
    def __init__(self) -> None:
        print("Loading embedding model...")
        self.model = SentenceTransformer(MODEL_NAME)
        print("Loading FAISS index...")
        self.index = load_faiss_index()
        self.words = load_words()
        self.word_to_idx: Dict[str, int] = {w: i for i, w in enumerate(self.words)}
        self.idx_to_word: Dict[int, str] = {i: w for i, w in enumerate(self.words)}
        self.state = SolverState()
        print(f"Solver ready. Vocabulary: {len(self.words)} words")

    def embed_word(self, word: str) -> np.ndarray:
        vec = self.model.encode([word], convert_to_numpy=True).astype(np.float32)
        return l2_normalize(vec)

    def get_neighbors(self, word: str, k: int = 50) -> List[str]:
        if word not in self.word_to_idx:
            vec = self.embed_word(word)
            _, indices = self.index.search(vec, k=k)
            neighbors = []
            for idx in indices[0]:
                w = self.idx_to_word.get(int(idx))
                if w and w not in self.state.tried_words:
                    neighbors.append(w)
            return neighbors[:k]

        vec = self.embed_word(word)
        _, indices = self.index.search(vec, k=k + 1)
        neighbors = []
        for idx in indices[0]:
            w = self.idx_to_word.get(int(idx))
            if w and w != word and w not in self.state.tried_words:
                neighbors.append(w)
        return neighbors[:k]

    def get_top_words_similar_to(self, word: str, k: int = 500) -> List[str]:
        """Get top-k words most similar to a given word (by embedding distance)."""
        vec = self.embed_word(word)
        _, indices = self.index.search(vec, k=k)
        result = []
        for idx in indices[0]:
            w = self.idx_to_word.get(int(idx))
            if w and w not in self.state.tried_words:
                result.append(w)
        return result

    def record_guess(self, word: str, rank: int) -> None:
        result = GuessResult(word=word, rank=rank)
        self.state.guesses.append(result)
        self.state.tried_words.add(word)
        self.state.guess_count += 1

        if rank < self.state.best_rank:
            self.state.best_rank = rank
            self.state.best_word = word

    def next_guess(self) -> Optional[str]:
        if self.state.best_rank == 1:
            return None

        if self.state.phase == "seed":
            for w in SEED_WORDS:
                if w not in self.state.tried_words and w in self.word_to_idx:
                    return w
            self.state.phase = "probe"
            return self.next_guess()

        if self.state.phase in ("probe", "chase"):
            if self.state.candidate_pool:
                return self.state.candidate_pool.pop(0)
            if self.state.best_word:
                neighbors = self.get_neighbors(self.state.best_word, k=50)
                if neighbors:
                    self.state.candidate_pool = neighbors
                    self.state.phase = "chase"
                    return neighbors[0]
            self.state.phase = "diversify"
            return self.next_guess()

        if self.state.phase == "diversify":
            random.shuffle(SEED_WORDS)
            for w in SEED_WORDS:
                if w not in self.state.tried_words and w in self.word_to_idx:
                    return w
            self.state.phase = "exhaust"
            return self.next_guess()

        if self.state.phase == "exhaust":
            for w in self.words:
                if w not in self.state.tried_words:
                    return w

        return None

    def process_feedback(self, word: str, rank: int) -> str:
        self.record_guess(word, rank)

        if rank == 1:
            return "solved"

        if rank <= 5:
            neighbors = self.get_neighbors(self.state.best_word, k=10)
            self.state.candidate_pool = neighbors
            self.state.phase = "chase"
        elif rank <= 20:
            neighbors = self.get_neighbors(self.state.best_word, k=25)
            self.state.candidate_pool = neighbors
            self.state.phase = "chase"
        elif rank <= 100:
            neighbors = self.get_neighbors(self.state.best_word, k=50)
            self.state.candidate_pool = neighbors
            self.state.phase = "chase"
        elif rank <= 500:
            if self.state.phase != "chase":
                neighbors = self.get_neighbors(self.state.best_word, k=50)
                self.state.candidate_pool = neighbors
                self.state.phase = "chase"
        else:
            if self.state.phase == "chase":
                self.state.phase = "diversify"

        return self.state.phase

    def get_status(self) -> str:
        total = self.state.guess_count
        best = self.state.best_rank
        best_w = self.state.best_word
        return (
            f"Guesses: {total} | Best: #{best} ({best_w}) | "
            f"Phase: {self.state.phase}"
        )

    def get_rank_against_word(self, guess: str, target: str) -> Tuple[int, List[str]]:
        """Compute rank of guess relative to target using FAISS (for testing).
        
        Ranks all words by similarity to target, then returns where guess falls.
        """
        target_vec = self.embed_word(target)
        _, sorted_indices = self.index.search(target_vec, k=self.index.ntotal)

        guess_rank = 999999
        for pos, idx in enumerate(sorted_indices[0], start=1):
            w = self.idx_to_word.get(int(idx))
            if w == guess:
                guess_rank = pos
                break

        top_words = []
        for idx in sorted_indices[0][:30]:
            w = self.idx_to_word.get(int(idx))
            if w:
                top_words.append(w)

        return guess_rank, top_words
