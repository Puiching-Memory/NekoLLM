# NekoLLM

## conda

conda create -n nekollm python=3.12
conda activate nekollm
pip3 install torch torchvision --index-url https://download.pytorch.org/whl/cu129
git clone --depth 1 https://github.com/hiyouga/LLaMA-Factory.git
cd LLaMA-Factory
pip install -e ".[torch,metrics]" --no-build-isolation


## web ui
llamafactory-cli webui

# 服务器部署板块

## 安装napcat
这个步骤会在ubuntu上安装napcat+QQ
curl -o napcat.sh https://raw.githubusercontent.com/NapNeko/napcat-linux-installer/refs/heads/main/install.sh && sudo bash napcat.sh
sudo bash ./launcher.sh

## 安装conda
wget https://ghfast.top/https://github.com/conda-forge/miniforge/releases/download/25.3.1-0/Miniforge3-25.3.1-0-Linux-x86_64.sh

## 安装schrc
wget https://ghfast.top/https://github.com/RubyMetric/chsrc/releases/download/v0.2.2/chsrc-x64-linux

conda create -n nonebot2 python=3.13
conda activate nonebot2

## 安装nonebot2
pip install ensurepath nb-cli
nb create
cd napcat-OneBotV11/
nb run

## 配置screen
screen -R nonebot2
screen -R napcat
screen -X -S <screen_name> quit

# 插件制作板块
pip install ensurepath nb-cli openai
nb create
nb plugin create
nb run

将DASHSCOPE_API_KEY写入powershell临时环境变量
$env:DASHSCOPE_API_KEY=""
linux
export DASHSCOPE_API_KEY=""
