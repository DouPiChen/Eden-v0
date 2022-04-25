# Eden-v0

# Installation Guide

## Prerequisite

This project works with python 3.8, and we recommend using Anaconda for convenience. We suppose you have followed the instructions from [Anaconda official page](https://www.anaconda.com/) to install Anaconda on your computer. 

Clone the project into your computer:

```bash
git clone https://github.com/DouPiChen/Eden-v0.git
cd EdenPublish
```

## Windows(expected to work on windows 10/11)

Execute the following commands in Anaconda Powershell Prompt from project root:

```powershell
conda create -n eden python=3.8
conda activate eden
pip install -e python/
```

If things go well, you are expected to get prompts like "Successfully installed eden-0.0.1", and now you can just try it off:

```powershell
python -m eden.interactive
```



## Linux

### General installation

Execute the following commands from project root:

```bash
conda create -n eden python=3.8 boost=1.73.0
conda activate eden
pip install -e python/
```

Try it off:

```bash
python -m eden.interactive
```



### Troubleshooting

We've tested the installation process on WSL Ubuntu20.04. However, if you're using other distributions, e.g., centOS 7 which is quite popular, you may have trouble finding .so files(mainly boost_python) inside the anaconda environments. In that case, you may add the anaconda library path in your LD_LIBRARY_PATH by yourself.

```bash
export LD_LIBRARY_PATH=${path_to_anaconda}/envs/eden/lib:$LD_LIBRARY_PATH
```

