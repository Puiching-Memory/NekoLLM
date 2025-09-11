import secrets
import string
import hashlib
from typing import Optional


class SecureTokenGenerator:
    """
    安全Token生成器类
    
    该类提供了生成高安全性Token的方法，使用Python的secrets模块确保生成的Token具有足够的熵。
    secrets模块专为生成加密强度高的随机数而设计，适用于管理密码、账户认证、安全令牌等。
    """
    
    @staticmethod
    def generate_api_key(length: int = 32) -> str:
        """
        生成安全的API密钥
        
        Args:
            length (int): API密钥长度，默认为32字符
            
        Returns:
            str: 生成的API密钥
            
        该方法使用secrets模块生成包含字母和数字的随机字符串。
        默认长度32提供了足够的安全强度（约192位熵）。
        """
        alphabet = string.ascii_letters + string.digits
        return ''.join(secrets.choice(alphabet) for _ in range(length))
    
    @staticmethod
    def generate_hex_token(length: int = 32) -> str:
        """
        生成十六进制格式的安全Token
        
        Args:
            length (int): Token字节数，默认为32字节（64字符）
            
        Returns:
            str: 生成的十六进制Token
            
        该方法使用secrets.token_hex生成十六进制格式的安全Token。
        """
        return secrets.token_hex(length)
    
    @staticmethod
    def generate_url_safe_token(length: int = 32) -> str:
        """
        生成URL安全的Token
        
        Args:
            length (int): Token字节数，默认为32字节
            
        Returns:
            str: 生成的URL安全Token
            
        该方法使用secrets.token_urlsafe生成适用于URL和文件名的安全Token。
        """
        return secrets.token_urlsafe(length)
    
    @staticmethod
    def generate_hashed_token(length: int = 32, hash_algorithm: str = 'sha256') -> tuple[str, str]:
        """
        生成带有哈希值的Token
        
        Args:
            length (int): 原始Token长度
            hash_algorithm (str): 哈希算法，默认为sha256
            
        Returns:
            tuple[str, str]: (原始Token, 哈希值)
            
        该方法生成一个Token及其哈希值，可用于需要验证Token但不存储原始Token的场景。
        """
        token = SecureTokenGenerator.generate_url_safe_token(length)
        hash_func = getattr(hashlib, hash_algorithm)
        hashed = hash_func(token.encode()).hexdigest()
        return token, hashed


def main():
    """
    Token生成工具的命令行接口
    """
    print("安全Token生成工具")
    print("=" * 30)
    
    # 生成不同类型的Token
    print(f"API密钥: {SecureTokenGenerator.generate_api_key()}")
    print(f"十六进制Token: {SecureTokenGenerator.generate_hex_token()}")
    print(f"URL安全Token: {SecureTokenGenerator.generate_url_safe_token()}")
    
    # 生成带哈希的Token
    token, hashed = SecureTokenGenerator.generate_hashed_token()
    print(f"带哈希Token: {token}")
    print(f"Token哈希值: {hashed}")


if __name__ == "__main__":
    main()