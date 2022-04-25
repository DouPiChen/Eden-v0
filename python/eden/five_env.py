import math
import numpy as np
from gym import spaces
from typing import Tuple, Dict, List, Any

from eden.core import Eden, MatEden


class FiveEden(Eden):
    def __init__(
            self,
            use_landform_map=False,
            **kwargs) -> None:
        """
        The type (or NameInt in the backend) of an object as well as landform will be mapped into a unique number.
        The map is: NameInt -> $CLASS_NAME_nameint_map[NameInt]
        
        Compact version
        """
        super().__init__(**kwargs)

        self.use_landform_map = use_landform_map
        if use_landform_map:
            print("FiveEden: using landform map")

        # Get the dict of landform/agent/being, etc. types. key is nameint, value is mapped observation representation
        offset = 2
        self._agent_nameint_map = {name_int: idx+offset for idx, name_int in enumerate(self.backend_cfg.agent_list)}
        offset += len(self.backend_cfg.agent_list)
        if use_landform_map:
            self._landform_nameint_map = {name_int: idx+offset for idx, name_int in enumerate(self.backend_cfg.landform_list)}
            offset += len(self.backend_cfg.landform_list)
        self._being_nameint_map = {name_int: idx+offset for idx, name_int in enumerate(self.backend_cfg.being_list)}
        offset += len(self.backend_cfg.being_list)
        self._item_nameint_map = {name_int: idx+offset for idx, name_int in enumerate(self.backend_cfg.item_list)}
        offset += len(self.backend_cfg.item_list)
        self._resource_nameint_map = {name_int: idx+offset for idx, name_int in enumerate(self.backend_cfg.resource_list)}
        offset += len(self.backend_cfg.resource_list)
        # self._buff_nameint_map = {name_int: idx+offset for idx, name_int in enumerate(self.backend_cfg.buff_list)}
        # offset += len(self.backend_cfg.buff_list)
        # self._weather_nameint_map = {name_int: idx+offset for idx, name_int in enumerate(self.backend_cfg.weather_list)}
        # offset += len(self.backend_cfg.weather_list)
        self.nameint_map_max_value = offset - 1

        self.nameint_map = {
            "agent": self._agent_nameint_map,
            # "landform": self._landform_nameint_map,
            "being": self._being_nameint_map,
            "item": self._item_nameint_map,
            "resource": self._resource_nameint_map,
            # "buff": self._buff_nameint_map,
            # "weather": self._weather_nameint_map
        }
        if use_landform_map:
            self.nameint_map['landform'] = self._landform_nameint_map

        # This is used to map them back
        self._agent_invmap = {idx: name_int for name_int, idx in self._agent_nameint_map.items()}
        if use_landform_map:
            self._landform_invmap = {idx: name_int for name_int, idx in self._landform_nameint_map.items()}
        self._being_invmap = {idx: name_int for name_int, idx in self._being_nameint_map.items()}
        self._item_invmap = {idx: name_int for name_int, idx in self._item_nameint_map.items()}
        self._resource_invmap = {idx: name_int for name_int, idx in self._resource_nameint_map.items()}
        # self._buff_invmap = {idx: name_int for name_int, idx in self._buff_nameint_map.items()}
        # self._weather_invmap = {idx: name_int for name_int, idx in self._weather_nameint_map.items()}
        self.invmap = {
            "agent": self._agent_invmap,
            # "landform": self._landform_invmap,
            "being": self._being_invmap,
            "item": self._item_invmap,
            "resource": self._resource_invmap,
            # "buff": self._buff_invmap,
            # "weather": self._weather_invmap
        }
        if use_landform_map:
            self.invmap['landform'] = self._landform_invmap

        # Long Tensor
        # Observation consists of:
        # 1. Unit section(all the values within self.nameint_map_max_value)
        #   an object map (full map size), a backpack map(backpack_size), an equipment map(slot size),
        #   a synthesis map(synthesize dict length size),
        # 2. Attribute section
        #   an attribute list, a backpack item number list
        self._object_map_length = self.map_size_y*self.map_size_x
        self._backpack_length = self.backpack_size
        self._equipment_length = self.equipment_size
        self._synthesize_length = len(self.synthesize_list)
        self.unit_section_length = self._object_map_length+self._backpack_length+self._equipment_length+self._synthesize_length

        self._attribute_length = len(self.attribute_name)
        self._backpack_count_length = self.backpack_size
        self.attribute_section_length = self._attribute_length + self._backpack_count_length

        self.landform_section_length = self.unit_section_length if self.use_landform_map else 0

        self.obs_length = self.unit_section_length + self.attribute_section_length + self.landform_section_length

        self.observation_space = spaces.Box(
            low=np.zeros((self._backend.agent_count, self.obs_length)),
            high=np.zeros((self._backend.agent_count, self.obs_length)) + np.inf,
            shape=(self._backend.agent_count, self.obs_length),
            dtype=np.float32
        )
        self.action_space = spaces.Tuple(
            [spaces.MultiDiscrete((len(self.backend_cfg.action_list), self.unit_section_length), dtype=np.int)
             for _ in range(self.backend.agent_count)])

    def step(self, action: Tuple[np.ndarray]) -> Tuple[np.ndarray, np.ndarray, bool, Dict[str, Any]]:
        tri_code_actions = []
        for idx, act in enumerate(action):
            tri_code_actions.append(self._select_action(idx, act[0], act[1]))
        # self._backend.update(tri_code_actions)
        obs = self._get_five_observation()
        _, reward, done, info = super().step(tri_code_actions)
        return obs, reward, done, info

    def _get_five_observation(self):
        # Get Agent Observe
        all_obs_orig = self._backend.observe()
        five_obs_list = []
        self._func_bar = []
        for obs_orig in all_obs_orig:
            five_obs = np.zeros(shape=(self.obs_length), dtype=np.int)
            if len(obs_orig) <= 0:
                five_obs_list.append(five_obs)
                continue
            basic_block, position_block, attribute_block, backpack_block, equipment_block, vis_agent_block, \
            vis_being_block, vis_item_block, vis_rsrc_block = self._obs_orig_parser(obs_orig)
            
            agent_x, agent_y = position_block

            # Object Map
            # Agent itself
            five_obs[int(agent_x)*self.map_size_x+int(agent_y)] = 1
            # agent
            for idx_vis_agent in range(0, len(vis_agent_block), 3):
                name_int = int(vis_agent_block[idx_vis_agent])
                vis_agent_type = self._agent_nameint_map[name_int]
                x, y = vis_agent_block[idx_vis_agent + 1:idx_vis_agent + 3]
                five_obs[int(x)*self.map_size_x + int(y)] = vis_agent_type
            # being
            for idx_vis_being in range(0, len(vis_being_block), 3):
                name_int = int(vis_being_block[idx_vis_being])
                vis_being_type = self._being_nameint_map[name_int]
                x, y = vis_being_block[idx_vis_being + 1:idx_vis_being + 3]
                five_obs[int(x)*self.map_size_x + int(y)] = vis_being_type
            # item
            for idx_vis_item in range(0, len(vis_item_block), 3):
                name_int = int(vis_item_block[idx_vis_item])
                vis_item_type = self._item_nameint_map[name_int]
                x, y = vis_item_block[idx_vis_item + 1:idx_vis_item + 3]
                five_obs[int(x)*self.map_size_x + int(y)] = vis_item_type
            # resource(rsrc)
            for idx_vis_rsrc in range(0, len(vis_rsrc_block), 3):
                name_int = int(vis_rsrc_block[idx_vis_rsrc])
                vis_rsrc_type = self._resource_nameint_map[name_int]
                x, y = vis_rsrc_block[idx_vis_rsrc + 1:idx_vis_rsrc + 3]
                five_obs[int(x)*self.map_size_x + int(y)] = vis_rsrc_type

            # Function Bar
            # backpack(item, type only)
            # equipment(item)
            # synthesize(item)
            _func_bar = [self._item_nameint_map[x] if x != -1 else 0 for x in backpack_block[::2]]
            _func_bar.extend([self._item_nameint_map[x] if x != -1 else 0 for x in equipment_block])
            _func_bar.extend([self._item_nameint_map[x] for x in self.synthesize_list])
            
            # Attribute Section
            _attribute_section = attribute_block + [x if x != -1 else 0 for x in backpack_block[1::2]]
            five_obs[self._object_map_length:self.obs_length-self.landform_section_length] = _func_bar + _attribute_section

            # Landform Section
            if self.use_landform_map:
                use_night_vision = (basic_block[1] < 0.5)
                vision = attribute_block[self.attribute_name.index("NightVision")] if use_night_vision \
                    else attribute_block[self.attribute_name.index("Vision")]
                agent_x, agent_y = position_block
                ui_info = self._backend.ui(0)
                # Landform Map
                for i in range(0, self.map_size_x):
                    for j in range(0, self.map_size_y):
                        if abs(i - agent_x) + abs(j - agent_y) > vision:
                            continue
                        else:
                            name_int = int(ui_info[(i * self.map_size_x + j) * 6 + 1])
                            five_obs[self.unit_section_length + self.attribute_section_length + i*self.map_size_x + j] = self._landform_nameint_map[name_int]



            five_obs_list.append(five_obs)
        self._last_obs = np.array(five_obs_list)
        return np.array(five_obs_list)

    def _select_action(self, agent_idx, input_act_type, unit_idx):
        act_type = int(input_act_type)
        # object map: (x-y)
        if unit_idx < self._object_map_length:
            param1 = int(unit_idx) // self.map_size_y
            param2 = int(unit_idx) % self.map_size_y
        # backpack, equipment and synthesize
        else:
            vis_unit_nameint = self._last_obs[agent_idx, unit_idx]
            if vis_unit_nameint == 0:
                act_type = 0
                param1 = 0
                param2 = 0
            elif vis_unit_nameint ==1:
                act_type = 0
                param1 = 0
                param2 = 0
            else:
                if act_type not in [4, 5, 6, 7]:
                    act_type = 0
                param1 = self._item_invmap[self._last_obs[agent_idx, unit_idx]]
                param2 = 1

        return [float(act_type), float(param1), float(param2)]

    @staticmethod
    def _obs_orig_parser(obs_orig):
        cursor = 0
        # part 1:basic information of env
        basic_block = obs_orig[cursor:cursor + 4]
        cursor += 4

        # part 2: basic information of agent
        position_block = obs_orig[cursor:cursor + 2]  # position
        cursor += 2

        attr_num = round(obs_orig[cursor])
        cursor += 1
        attribute_block = obs_orig[cursor:cursor + attr_num]  # attribute
        cursor += attr_num

        # part 3: backpack and equipment
        backpack_num = round(obs_orig[cursor] * 2)
        cursor += 1
        backpack_block = obs_orig[cursor:cursor + backpack_num]  # backpack
        cursor += backpack_num

        equipment_num = round(obs_orig[cursor])
        cursor += 1
        equipment_block = obs_orig[cursor:cursor + equipment_num]  # equipment
        cursor += equipment_num

        # part 4: find the nearest agent,being,resource
        agent_num = round(obs_orig[cursor] * 3)
        cursor += 1
        vision_agent_block = obs_orig[cursor:cursor + agent_num]
        cursor += agent_num

        being_num = round(obs_orig[cursor] * 3)
        cursor += 1
        vision_being_block = obs_orig[cursor:cursor + being_num]
        cursor += being_num

        resource_num = round(obs_orig[cursor] * 3)
        cursor += 1
        vision_resource_block = obs_orig[cursor:cursor + resource_num]
        cursor += resource_num

        item_num = round(obs_orig[cursor] * 3)
        cursor += 1
        vision_item_block = obs_orig[cursor:cursor + item_num]
        cursor += item_num

        return basic_block, position_block, attribute_block, backpack_block, equipment_block, vision_agent_block, \
               vision_being_block, vision_item_block, vision_resource_block

    def reset(self, seed: int = 0) -> np.ndarray:
        super().reset(seed)
        return self._get_five_observation()
