"""Experiment: see what embeddings are and how similarity works."""

import numpy as np
from chromadb.utils.embedding_functions import DefaultEmbeddingFunction

embed = DefaultEmbeddingFunction()  # small local model (all-MiniLM-L6-v2)

question = "where can I get cheap food?"
chunks = [
    "Budget eateries and inexpensive dumplings can be found in Chinatown.",
    "Myki cards are needed to pay tram and train fares.",
    "The Great Ocean Road is a scenic coastal drive west of the city.",
]

vectors = embed([question] + chunks)
print("Each text became", len(vectors[0]), "numbers")
print("First 5 numbers of the question:", np.round(vectors[0][:5], 3))
print()


def similarity(a, b):
    """Cosine similarity: 1 = same meaning, 0 = unrelated."""
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))


for chunk, vector in zip(chunks, vectors[1:]):
    print(f"{similarity(vectors[0], vector):.2f}  {chunk}")