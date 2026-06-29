def test_embed_returns_list_of_floats(embedder):
    """Test that embed returns a list of floats."""
    result = embedder.embed("Test text")

    assert isinstance(result, list)
    assert len(result) == 384  # all-MiniLM-L6-v2 dimension
    assert all(isinstance(x, float) for x in result)


def test_embed_same_text_same_embedding(embedder):
    """Test that same text produces same embedding."""
    text = "Test text for embedding"
    result1 = embedder.embed(text)
    result2 = embedder.embed(text)

    assert result1 == result2


def test_embed_batch(embedder):
    """Test batch embedding."""
    texts = ["First text", "Second text", "Third text"]
    results = embedder.embed_batch(texts)

    assert len(results) == 3
    assert all(len(r) == 384 for r in results)


def test_embed_empty_string(embedder):
    """Test embedding empty string (edge case)."""
    result = embedder.embed("")
    assert isinstance(result, list)
    assert len(result) == 384
