import os
import numpy as np
from typing import List

import eden.backend.eden_py as cpp_game

class Backend:
    def __init__(self, config_dir:str) -> None:
        """
        """
        self._cppbackend = cpp_game.Env(config_dir)

    def update(self, actions) -> None:
        if type(actions) is np.ndarray:
            assert(len(actions.shape) == 2), "action dim should be 2"
            actions = actions.astype(np.float32).tolist()
        else:
            assert(type(actions) is list), "action is neither numpy array nor list"
        print(actions)
        self._cppbackend.update(actions)

    def reset(self, seed:int = 0) -> None:
        self._cppbackend.reset(seed)

    def run_script(self, script:str) -> str:
        return self._cppbackend.run_script(script)

    def observe(self) -> List[List[float]]:
        return self._cppbackend.observe()

    def result(self) -> List[List[float]]:
        return self._cppbackend.result()
    
    def ui(self, agent_id: int) -> List[float]:
        return self._cppbackend.get_ui(agent_id)

    @property
    def agent_count(self) -> int:
        return self._cppbackend.agent_count()[0]
    

def create(config_dir:str) -> Backend:
    if not os.path.exists(config_dir):
        raise FileNotFoundError(f"config directory {config_dir} not found.")
    return Backend(config_dir=config_dir)