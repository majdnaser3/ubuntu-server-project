
import pytest

from client.src.main import normalize_url


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("http://192.168.1.100:8000", "http://192.168.1.100:8000"),
        (" https://server.example.com/ ", "https://server.example.com"),
        ("http://localhost:8000/", "http://localhost:8000"),
    ],
)
def test_normalize_url_accepts_valid_urls(value, expected):
    assert normalize_url(value) == expected


@pytest.mark.parametrize(
    "value",
    [
        "",
        "192.168.1.100:8000",
        "ftp://server.example.com",
        "http://",
        "http://user:password@example.com",
        "http://example.com/path",
        "http://example.com/?token=secret",
        "http://example.com/#section",
    ],
)
def test_normalize_url_rejects_invalid_urls(value):
    with pytest.raises(ValueError):
        normalize_url(value)
