import os
from eden.wrappers.reward import Reward
import gym
import math
import json
import numpy as np
import eden.backend.interface as game
from eden.backend.config import BackendConfig
from gym import spaces
from collections import OrderedDict
from typing import List, Optional, Tuple, Dict, Any


class Eden(gym.Env):
    def __init__(
            self,
            config_dir='./config',
            empty_info=False
    ) -> None:

        self._backend = game.create(config_dir)
        self._backend_cfg = BackendConfig(config_dir)
        self.empty_info = empty_info

        done_filepath = os.path.join(config_dir, "game_done.json")
        score_filepath = os.path.join(config_dir, 'score.json')
        assert os.path.exists(done_filepath), f"{done_filepath} does not exist"
        assert os.path.exists(score_filepath), f"{score_filepath} does not exist"
        self.done_condition = json.load(open(done_filepath, 'r'))
        self.reward_table   = json.load(open(score_filepath, 'r'))

        self.total_step = 0
        self.prev_obs = None
        self.curr_obs = None
        self.results = None

        self.map_size_x = int(self.backend_cfg.general_dict['MapSizeX'])
        self.map_size_y = int(self.backend_cfg.general_dict['MapSizeY'])
        self.synthesize_list = self.backend_cfg.synthesis_list
        self.backpack_size = int(list(self.backend_cfg.agent_dict.values())[0]['BackpackSize'])
        self.equipment_size = len(list(self.backend_cfg.agent_dict.values())[0]['Slot'].split(';'))
        self.attribute_name = list(list(self.backend_cfg.agent_dict.values())[0]['Attribute'].keys())

        # agent's observation_space and action_space variate in Eden env
        self.action_space = None
        self.observation_space = None

    def step(self, action: np.ndarray) -> Tuple[np.ndarray, np.ndarray, bool, Dict[str, Any]]:
        self.total_step += 1
        self._backend.update(action)
        self.prev_obs = self.curr_obs
        self.curr_obs = np.array(self._backend.observe())
        self.results = self._backend.result()
        done = self._done()
        info = self._info(action)
        reward = self._reward(info)
        return self.curr_obs, reward, done, info

    def reset(self, seed: int = 0) -> np.ndarray:
        self._backend.reset(seed)
        self.total_step = 0
        self.prev_obs = None
        self.curr_obs = np.array(self._backend.observe())
        self.results = None
        return self.curr_obs

    def run_script(self, script: str) -> str:
        return self._backend.run_script(script)

    def _reward(self, info):
        rewards = []
        for action_result in info:
            # action
            reward = self._action_reward(action_result)
            # attribute
            attr_icrem = action_result['attr_increment']
            for key in attr_icrem.keys():
                if key in self.reward_table['Attribute'].keys():
                    reward += attr_icrem[key] * self.reward_table['Attribute'][key]
                else:
                    reward += attr_icrem[key] * self.reward_table['Attribute']['default']
            # dead
            if action_result['dead'] is True:
                reward += self.reward_table['Dead']
            # position
            if action_result['position'] in self.reward_table['ScorePoint'].keys():
                reward += self.reward_table['ScorePoint'][action_result['position']]
            rewards.append(reward)
        return rewards

    def _action_reward(self, action_result):
        reward = 0
        if 'Idle' in action_result['action'] :
            result = self.reward_table['Idle']
            reward = result['default']
        elif 'Attack' in action_result['action']:
            result = self.reward_table['Attack']
            if 'fail' in action_result['result']:
                reward = result['fail']
            else:
                if action_result['target'] not in list(result.keys()):
                    reward = result['default_' + action_result['result']]
                else:
                    reward = result[action_result['target']+'_'+action_result['result']]
        elif 'Collect' in action_result['action']:
            result = self.reward_table['Collect']
            if 'fail' in action_result['result']:
                reward = result['fail']
            else:
                if action_result['target'] not in list(result.keys()):
                    reward = result['default']
                else:
                    reward = result[action_result['target']]
        elif 'Discard' in action_result['action']:
            result = self.reward_table['Discard']
            if 'fail' in action_result['result']:
                reward = result['fail']
            else:
                if action_result['target'] not in list(result.keys()):
                    reward = result['default']
                else:
                    reward = result[action_result['target']]
                reward *= float(action_result['result'])
        elif 'Move' in action_result['action']:
            result = self.reward_table['Move']
            if 'fail' in action_result['result']:
                reward = result['fail']
            else:
                reward = result['default']
        elif 'Synthesize' in action_result['action']:
            result = self.reward_table['Synthesize']
            if 'fail' in action_result['result']:
                reward = result['fail']
            else:
                if action_result['target'] not in list(result.keys()):
                    reward = result['default']
                else:
                    reward = result[action_result['target']]
                reward *= float(action_result['result'])
        elif 'Pickup' in action_result['action']:
            result = self.reward_table['Pickup']
            if 'fail' in action_result['result']:
                reward = result['fail']
            else:
                if action_result['target'] not in list(result.keys()):
                    reward = result['default']
                else:
                    reward = result[action_result['target']]
                reward *= float(action_result['result'])
        elif 'Equip' in action_result['action']:
            result = self.reward_table['Equip']
            if 'fail' in action_result['result']:
                reward = result['fail']
            else:
                if action_result['target'] not in list(result.keys()):
                    reward = result['default_' + action_result['result']]
                else:
                    reward = result[action_result['target']+'_'+action_result['result']]
        elif 'Consume' in action_result['action']:
            result = self.reward_table['Consume']
            if 'fail' in action_result['result']:
                reward = result['fail']
            else:
                if action_result['target'] not in list(result.keys()):
                    reward = result['default']
                else:
                    reward = result[action_result['target']]
        return reward

    def _info(self, action):
        if self.empty_info:
            return []
        info = []
        for agent_id, result in enumerate(self.results):
            if len(self.curr_obs[agent_id]) < 1:
                info.append({
                    'position': 'None',
                    'action': 'None',
                    'attr_increment': {},
                    'dead': True
                })
                continue
            # position
            position = f"{int(self.curr_obs[agent_id][4])}-{int(self.curr_obs[agent_id][5])}"
            # action
            action_name = self._backend_cfg.action_list[int(result[0])]
            # target
            target = 'None'
            if action_name == 'Move':
                target = f"({int(action[agent_id][1])},{int(action[agent_id][2])})"
            elif action_name != 'Idle':
                type_name = self._backend_cfg.type_list[int(result[1])]
                type_id = f"{type_name}:{int(result[2])}"
                if type_id in self._backend_cfg.typeid2name.keys():
                    target = self._backend_cfg.typeid2name[type_id]
            # result
            result_int = int(result[3])
            result_str = 'fail'
            if action_name == 'Attack':
                if result_int == 1:
                    result_str = 'hit'
                elif result_int == 2:
                    result_str = 'kill'
            elif action_name == 'Equip':
                if result_int == 1:
                    result_str = 'equip'
                elif result_int == 2:
                    result_str = 'undress'
            elif action_name in ['Pickup', 'Discard', 'Synthesize']:
                if result_int > 0:
                    result_str = str(result_int)
            else:
                if result_int > 0:
                    result_str = 'success'
            # attribute increment
            name_int = int(result[4])
            increment = {}
            if self.prev_obs is not None:
                for attribute_id in range(int(self.curr_obs[agent_id][6])):
                    delta = self.curr_obs[agent_id][7 + attribute_id] - self.prev_obs[agent_id][7 + attribute_id]
                    if abs(delta) > 1e-4:
                        increment[self.backend_cfg.attribute_dict[name_int][attribute_id]] = delta
            info.append({
                'position': position,
                'action': action_name,
                'target': target,
                'result': result_str,
                'attr_increment': increment,
                'dead': False
            })
        return info
    
    def _done(self) -> np.ndarray:
        done = np.zeros((self._backend.agent_count), dtype=bool)
        for agent_id, (obs, result) in enumerate(zip(self.curr_obs, self.results)):
            if len(obs) < 1:
                done[agent_id] = True
                continue
            # position
            if list(obs[4:6]) in self.done_condition["position"]:
                done[agent_id] = True
                continue
            # attribute
            name_int = result[4]
            for attr_id, attr_value in enumerate(obs[7:7+int(obs[6])]):
                attr_name = self._backend_cfg.attribute_dict[name_int][attr_id]
                if attr_name in self.done_condition["attribute"].keys():
                    if attr_value <= self.done_condition["attribute"][attr_name]:
                        done[agent_id] = True
                        break
            if done[agent_id]:
                continue
            # backpack
            cursor = 8 + int(obs[6])
            for bp_slot in range(self.backpack_size):
                name_int = int(obs[cursor + bp_slot * 2])
                if name_int < 0:
                    continue
                name = self._backend_cfg.typeid2name[f'item:{name_int}']
                count = int(obs[cursor + bp_slot * 2 + 1])
                if name in self.done_condition["backpack"]:
                    if count >= self.done_condition["backpack"][name]:
                        done[agent_id] = True
                        break
            if done[agent_id]:
                continue
            # equipment
            cursor += self.backpack_size * 2 + 1
            for eq_slot in range(self.equipment_size):
                name_int = int(obs[cursor + eq_slot])
                if name_int < 0:
                    continue
                name = self._backend_cfg.typeid2name[f'item:{name_int}']
                if name in self.done_condition["equipment"]:
                    done[agent_id] = True
                    break
        return done

    @property
    def obs(self) -> np.ndarray:
        return np.array(self._backend.observe())

    @property
    def backend(self):
        return self._backend

    @property
    def backend_cfg(self):
        return self._backend_cfg


class MatEden(Eden):
    def __init__(
            self,
            multiplier=20,
            **kwargs) -> None:
        """
        The type (or NameInt in the backend) of an object as well as landform will be mapped into a unique number.
        The map is: NameInt -> $CLASS_NAME_nameint_map[NameInt]

        """
        super().__init__(**kwargs)

        # Get the dict of landform/agent/being, etc. types. key is nameint, value is mapped observation representation
        self._agent_nameint_map = {name_int: idx for idx, name_int in enumerate(self.backend_cfg.agent_list)}
        self._landform_nameint_map = {name_int: idx for idx, name_int in enumerate(self.backend_cfg.landform_list)}
        self._being_nameint_map = {name_int: idx for idx, name_int in enumerate(self.backend_cfg.being_list)}
        self._item_nameint_map = {name_int: idx for idx, name_int in enumerate(self.backend_cfg.item_list)}
        self._resource_nameint_map = {name_int: idx for idx, name_int in enumerate(self.backend_cfg.resource_list)}
        self._buff_nameint_map = {name_int: idx for idx, name_int in enumerate(self.backend_cfg.buff_list)}
        self._weather_nameint_map = {name_int: idx for idx, name_int in enumerate(self.backend_cfg.weather_list)}

        max_length = max((len(self._agent_nameint_map), len(self._landform_nameint_map), len(self._being_nameint_map),
                          len(self._item_nameint_map), len(self._resource_nameint_map), len(self._buff_nameint_map),
                          len(self._weather_nameint_map)))
        # Get the multiplier of landform/agent/being, etc. types
        self.multiplier = multiplier
        if self.multiplier < max_length:
            raise AssertionError("MatEden: given multiplier smaller than object type counts, may lead to conflict")
        self.object_type_list = ["agent", "landform", "being", "item", "resource", "buff", "weather"]
        self.multiplier_dict = OrderedDict({
            "agent": 0,
            "landform": 1,
            "being": 2,
            "item": 3,
            "resource": 4,
            "buff": 5,
            "weather": 6
        })
        for k in self.multiplier_dict.keys():
            self.multiplier_dict[k] *= self.multiplier

        for k in self._agent_nameint_map.keys():
            self._agent_nameint_map[k] += self.multiplier_dict["agent"]
        for k in self._landform_nameint_map.keys():
            self._landform_nameint_map[k] += self.multiplier_dict["landform"]
        for k in self._being_nameint_map.keys():
            self._being_nameint_map[k] += self.multiplier_dict["being"]
        for k in self._item_nameint_map.keys():
            self._item_nameint_map[k] += self.multiplier_dict["item"]
        for k in self._resource_nameint_map.keys():
            self._resource_nameint_map[k] += self.multiplier_dict["resource"]
        for k in self._buff_nameint_map.keys():
            self._buff_nameint_map[k] += self.multiplier_dict["buff"]
        for k in self._weather_nameint_map.keys():
            self._weather_nameint_map[k] += self.multiplier_dict["weather"]
        self.nameint_map = {
            "agent": self._agent_nameint_map,
            "landform": self._landform_nameint_map,
            "being": self._being_nameint_map,
            "item": self._item_nameint_map,
            "resource": self._resource_nameint_map,
            "buff": self._buff_nameint_map,
            "weather": self._weather_nameint_map
        }

        # This is used to map them back
        self._agent_invmap = {idx: name_int for name_int, idx in self._agent_nameint_map.items()}
        self._landform_invmap = {idx: name_int for name_int, idx in self._landform_nameint_map.items()}
        self._being_invmap = {idx: name_int for name_int, idx in self._being_nameint_map.items()}
        self._item_invmap = {idx: name_int for name_int, idx in self._item_nameint_map.items()}
        self._resource_invmap = {idx: name_int for name_int, idx in self._resource_nameint_map.items()}
        self._buff_invmap = {idx: name_int for name_int, idx in self._buff_nameint_map.items()}
        self._weather_invmap = {idx: name_int for name_int, idx in self._weather_nameint_map.items()}
        self.invmap = {
            "agent": self._agent_invmap,
            "landform": self._landform_invmap,
            "being": self._being_invmap,
            "item": self._item_invmap,
            "resource": self._resource_invmap,
            "buff": self._buff_invmap,
            "weather": self._weather_invmap
        }

        # Get the shape of observation matrix
        # Observation consists of an object map (full map size), a backpack map(backpack_size), an
        # equipment map(slot size), a synthesis map(synthesize dict length size), an attribute list.
        self.obs_width = self.map_size_y
        self.obs_height = self.map_size_x * 2
        self.obs_height += math.ceil(
            (self.backpack_size +
             self.equipment_size +
             len(self.synthesize_list) +
             len(self.attribute_name)) / self.map_size_y)
        self.observation_space = spaces.Box(
            low=np.zeros((self._backend.agent_count, self.obs_height, self.obs_width)) - 1,
            high=np.zeros((self._backend.agent_count, self.obs_height, self.obs_width)) + np.inf,
            shape=(self._backend.agent_count, self.obs_height, self.obs_width),
            dtype=np.float32
        )
        # print("MatEden observation space: ", self.observation_space)
        self.action_space = spaces.Tuple(
            [spaces.MultiDiscrete((2, self.obs_height, self.obs_width), dtype=np.int)
             for _ in range(self.backend.agent_count)])
        # print("MatEden action space: ", self.action_space)

    def step(self, action: Tuple[np.ndarray]) -> Tuple[np.ndarray, np.ndarray, bool, Dict[str, Any]]:
        tri_code_actions = []
        for idx, act in enumerate(action):
            tri_code_actions.append(self._select_action(idx, act[1], act[2], act[0]))
        # self._backend.update(tri_code_actions)
        obs = self._get_mat_observation()
        _, reward, done, info = super().step(tri_code_actions)
        return obs, reward, done, info

    def _get_mat_observation(self):
        # Get Agent Observe
        all_obs_orig = self._backend.observe()
        obs_mats = []
        self._func_bar = []
        for obs_orig in all_obs_orig:
            obs_mat = np.zeros(shape=(self.obs_height, self.obs_width), dtype=np.int) - 1
            if len(obs_orig) <= 0:
                obs_mats.append(obs_mat)
                continue
            basic_block, position_block, attribute_block, backpack_block, equipment_block, vis_agent_block, \
            vis_being_block, vis_item_block, vis_rsrc_block = self._obs_orig_parser(obs_orig)
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
                        obs_mat[i, j] = self._landform_nameint_map[name_int]

            # Object Map
            # Agent itself
            obs_mat[int(agent_x) + self.map_size_x, int(agent_y)] = 1
            # agent
            for idx_vis_agent in range(0, len(vis_agent_block), 3):
                name_int = int(vis_agent_block[idx_vis_agent])
                vis_agent_type = self._agent_nameint_map[name_int]
                x, y = vis_agent_block[idx_vis_agent + 1:idx_vis_agent + 3]
                obs_mat[int(x) + self.map_size_x, int(y)] = vis_agent_type
            # being
            for idx_vis_being in range(0, len(vis_being_block), 3):
                name_int = int(vis_being_block[idx_vis_being])
                vis_being_type = self._being_nameint_map[name_int]
                x, y = vis_being_block[idx_vis_being + 1:idx_vis_being + 3]
                obs_mat[int(x) + self.map_size_x, int(y)] = vis_being_type
            # item
            for idx_vis_item in range(0, len(vis_item_block), 3):
                name_int = int(vis_item_block[idx_vis_item])
                vis_item_type = self._item_nameint_map[name_int]
                x, y = vis_item_block[idx_vis_item + 1:idx_vis_item + 3]
                obs_mat[int(x) + self.map_size_x, int(y)] = vis_item_type
            # resource(rsrc)
            for idx_vis_rsrc in range(0, len(vis_rsrc_block), 3):
                name_int = int(vis_rsrc_block[idx_vis_rsrc])
                vis_rsrc_type = self._resource_nameint_map[name_int]
                x, y = vis_rsrc_block[idx_vis_rsrc + 1:idx_vis_rsrc + 3]
                obs_mat[int(x) + self.map_size_x, int(y)] = vis_rsrc_type

            # Function Bar
            # backpack(item, type only)
            # equipment(item)
            # synthesize(item)
            # attribute(number only)
            _func_bar = [self._item_nameint_map[x] if x != -1 else -1 for x in backpack_block[::2]]
            _func_bar.extend([self._item_nameint_map[x] if x != -1 else -1 for x in equipment_block])
            _func_bar.extend([self._item_nameint_map[x] for x in self.synthesize_list])
            _func_bar.extend(attribute_block)
            self._func_bar.append(_func_bar)
            cursor = 0
            for i in range(self.map_size_x * 2, self.obs_height):
                for j in range(self.map_size_y):
                    obs_mat[i, j] = _func_bar[cursor]
                    cursor += 1
                    if cursor >= len(_func_bar):
                        break
            obs_mats.append(obs_mat)
        self._last_obs = np.array(obs_mats)
        return np.array(obs_mats)

    def _select_action(self, index, input_x, input_y, act_bool_type):
        act_type = 0
        param1 = input_x
        param2 = input_y
        # Landform map: Move
        if input_x < self.map_size_x:
            act_type = 8
        # Object map
        elif input_x < self.map_size_x * 2:
            x = input_x - self.map_size_x
            y = input_y
            curious_point = self._last_obs[index, input_x, input_y]
            if curious_point == -1:
                return [0., 0., 0.]
            object_type = self.object_type_list[curious_point // self.multiplier]
            param1 = x
            param2 = y
            if object_type == "agent":
                act_type = 2 if act_bool_type == 0 else 1
            elif object_type == "landform":  # Anyway this is impossible
                pass
            elif object_type == "being":
                act_type = 2 if act_bool_type == 0 else 1
            elif object_type == "item":
                act_type = 3
            elif object_type == "resource":
                act_type = 2
            elif object_type == "buff":
                pass
            elif object_type == "weather":
                pass
        # Function Bar
        else:
            func_bar_index = (input_x - self.map_size_x * 2) * self.map_size_y + input_y
            if func_bar_index >= len(self._func_bar[index]): return [0., 0., 0.]
            curious_point = self._func_bar[index][func_bar_index]
            if curious_point == -1:
                return [0., 0., 0.]
            if func_bar_index < self.backpack_size:  # Backpack
                item_nameint = self._item_invmap[curious_point]
                param1 = item_nameint
                param2 = 1
                if act_bool_type == 1:
                    act_type = 7
                else:
                    if item_nameint in [int(x.split(':')[-1]) for x in self.backend_cfg.equip_list]:  # Equipment
                        act_type = 5
                    else:  # Food
                        act_type = 4
            elif func_bar_index < self.backpack_size + self.equipment_size:  # Equipment
                act_type = 5
                item_nameint = self._item_invmap[curious_point]
                param1 = item_nameint
                param2 = 1
            elif func_bar_index < self.backpack_size + self.equipment_size + len(self.synthesize_list):  # Synthesize
                act_type = 6
                item_nameint = self._item_invmap[curious_point]
                param1 = item_nameint
                param2 = 1
            else:  # Attribute
                act_type = 0
                param1 = 0
                param2 = 0
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
        return self._get_mat_observation()
