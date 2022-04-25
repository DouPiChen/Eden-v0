# Eden-v0

Eden-v0 is a survival sandbox game framework that support single-player and multi-player survival challenges. Some games are configured games through this framework, and an demo is shown below. In each of these configured games, the agents need to explore the environment and utilize resources, while satisfying their metabolic consumption. They also need to deal with potential threats, such as changeable weather, ferocious beasts, unexpected unknown events, etc. Of course, the agents can use the acquired resources to synthesize and use them to strengthen themselves to deal with more dangerous enemies. The ultimate goal of the player is only one: to survive for a long time!

![](.\screenshots\demo.gif)

To survive for a long time is a meaningful and difficult goal in a complex and changeable environment. Our ancestors could only survive in places where dinosaurs could not see in the Jurassic, but now we humans have the ability to change the ecology of the earth. During this period, countless creatures which are taller, faster and stronger than us humans have all become extinct. In this process, the goal of long-term survival on earth has promoted the generation and continuous development of human intelligence. To achieve the goal, there are mainly two kinds of difficulties. First, it is difficult to adapt to the basic rules of the complex environment, which lions and tigers do better than humans. Then, when there are some sudden changes in the environment, such as small-probability events such as volcanic eruptions, tsunamis, etc., it is more difficult for these organisms to understand and use the preceding rules to survive in the long term.

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

