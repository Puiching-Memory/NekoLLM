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