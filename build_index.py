from __future__ import annotations

from typing import List

import numpy as np
from sentence_transformers import SentenceTransformer
from tqdm import tqdm

from utils import (
    build_faiss_index,
    generate_vocabulary,
    l2_normalize,
    save_embeddings,
    save_faiss_index,
    save_words,
)

MODEL_NAME = "all-MiniLM-L6-v2"


def embed_words(
    model: SentenceTransformer, words: List[str], batch_size: int = 256
) -> np.ndarray:
    embeddings_batches = []
    for start in tqdm(range(0, len(words), batch_size), desc="Embedding words"):
        batch = words[start : start + batch_size]
        emb = model.encode(batch, show_progress_bar=False, convert_to_numpy=True)
        embeddings_batches.append(emb)

    embeddings = np.vstack(embeddings_batches).astype(np.float32)
    return l2_normalize(embeddings)


def main() -> None:
    print("Generating vocabulary...")
    words = generate_vocabulary(target_size=50_000, min_length=2)
    print(f"Vocabulary size: {len(words)} words")
    save_words(words)

    print(f"Loading model: {MODEL_NAME}")
    model = SentenceTransformer(MODEL_NAME)

    print("Computing embeddings...")
    embeddings = embed_words(model, words)
    save_embeddings(embeddings)

    print("Building FAISS index...")
    index = build_faiss_index(embeddings)
    save_faiss_index(index)

    print(
        f"Saved {len(words)} words, embeddings matrix {embeddings.shape}, "
        f"and FAISS index to data/"
    )


if __name__ == "__main__":
    main()
