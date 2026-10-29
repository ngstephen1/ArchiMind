"""Explicit offline index creation; never acquire models during a build/search."""

import argparse
from pathlib import Path

from archimind.retrieval.eligibility import build_index
from archimind.retrieval.embedding_index import (
    build_embedding_index,
    write_embedding_index,
)
from archimind.retrieval.offline_encoder import FastEmbedCPUEncoder


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model-directory", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    from evaluate_furniture_embeddings import offline_bootstrap

    offline_bootstrap()
    encoder = FastEmbedCPUEncoder(args.model_directory)
    write_embedding_index(build_embedding_index(build_index(), encoder), args.output)
    print("Created derived local index", args.output)


if __name__ == "__main__":
    main()
