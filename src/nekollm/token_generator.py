from __future__ import annotations

import hashlib
import secrets
import string
from typing import Tuple

__all__ = [
    "SecureTokenGenerator",
    "generate_api_key",
    "generate_hex_token",
    "generate_url_safe_token",
    "generate_hashed_token",
    "main",
]


class SecureTokenGenerator:
    """Utility helpers for generating secure API tokens."""

    @staticmethod
    def generate_api_key(length: int = 32) -> str:
        alphabet = string.ascii_letters + string.digits
        return "".join(secrets.choice(alphabet) for _ in range(length))

    @staticmethod
    def generate_hex_token(length: int = 32) -> str:
        return secrets.token_hex(length)

    @staticmethod
    def generate_url_safe_token(length: int = 32) -> str:
        return secrets.token_urlsafe(length)

    @staticmethod
    def generate_hashed_token(length: int = 32, hash_algorithm: str = "sha256") -> Tuple[str, str]:
        token = SecureTokenGenerator.generate_url_safe_token(length)
        hash_func = getattr(hashlib, hash_algorithm)
        hashed = hash_func(token.encode()).hexdigest()
        return token, hashed


def generate_api_key(length: int = 32) -> str:
    return SecureTokenGenerator.generate_api_key(length)


def generate_hex_token(length: int = 32) -> str:
    return SecureTokenGenerator.generate_hex_token(length)


def generate_url_safe_token(length: int = 32) -> str:
    return SecureTokenGenerator.generate_url_safe_token(length)


def generate_hashed_token(length: int = 32, hash_algorithm: str = "sha256") -> Tuple[str, str]:
    return SecureTokenGenerator.generate_hashed_token(length, hash_algorithm)


def main() -> None:
    print("安全Token生成工具")
    print("=" * 30)

    print(f"API密钥: {generate_api_key()}")
    print(f"十六进制Token: {generate_hex_token()}")
    print(f"URL安全Token: {generate_url_safe_token()}")

    token, hashed = generate_hashed_token()
    print(f"带哈希Token: {token}")
    print(f"Token哈希值: {hashed}")


if __name__ == "__main__":
    main()
