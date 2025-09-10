# NekoLLM

# 服务器部署板块

## 安装napcat
这个步骤会在ubuntu上安装napcat+QQ
curl -o napcat.sh https://raw.githubusercontent.com/NapNeko/napcat-linux-installer/refs/heads/main/install.sh && sudo bash napcat.sh
sudo bash ./launcher.sh

## 安装环境
wget https://ghfast.top/https://github.com/conda-forge/miniforge/releases/download/25.3.1-0/Miniforge3-25.3.1-0-Linux-x86_64.sh
wget https://ghfast.top/https://github.com/RubyMetric/chsrc/releases/download/v0.2.2/chsrc-x64-linux

conda create -n napcatbot python=3.13
conda activate napcatbot

pip install ncatbot

## 配置screen
screen -R napcatBot
screen -R napcatQQ
screen -X -S <screen_name> quit

# 插件制作板块


## 将DASHSCOPE_API_KEY写入powershell临时环境变量
$env:DASHSCOPE_API_KEY=""
linux
export DASHSCOPE_API_KEY=""
