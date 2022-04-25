from gym.envs.registration import register
from eden.core import *
from eden.five_env import FiveEden

register(
    id='eden-v0',
    entry_point='eden:Eden',
)

register(
    id='eden-v1',
    entry_point='eden:MatEden'
)

register(
    id='eden-v2',
    entry_point='eden:FiveEden'
)