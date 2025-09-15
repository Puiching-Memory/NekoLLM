# NekoLLM

## 安装环境
wget https://ghfast.top/https://github.com/conda-forge/miniforge/releases/download/25.3.1-0/Miniforge3-25.3.1-0-Linux-x86_64.sh
wget https://ghfast.top/https://github.com/RubyMetric/chsrc/releases/download/v0.2.2/chsrc-x64-linux

conda create -n ncatbot python=3.13
conda activate ncatbot
pip install -r requirements.txt

## 配置screen
screen -R ncatbot
screen -X -S ncatbot quit

## 将DASHSCOPE_API_KEY写入临时环境变量

```bash
$env:DASHSCOPE_API_KEY=""
export DASHSCOPE_API_KEY=""
```

## 将API_TOKEN_TOOLS写入系统环境变量

```bash
$env:API_TOKEN_TOOLS=""
export API_TOKEN_TOOLS=""
```

## 启动
python main.py