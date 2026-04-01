"""
config.py — CS-Scout 服务端配置
复制此文件为 config.py 并填入实际值
"""

HOST = "0.0.0.0"
PORT = 5000

# 访问密钥，前端请求时需携带
SECRET_KEY = "your_secret_key_here"

# 服务端根目录（绝对路径）
BASE_DIR = "/home/ubuntu/server"

# 热力图和分析结果输出目录
OUTPUT_DIR = BASE_DIR + "/output"

# Demo 下载存储目录
DEMO_DIR = BASE_DIR + "/demos_opponents"
