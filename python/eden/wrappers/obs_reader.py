from gym import spaces
from gym import ObservationWrapper
import numpy as np


class ObsReader(ObservationWrapper):
    """
        Read the original observation of agents, and returns several structural obs in dict type.
        Every obs in this dict is obs of some agent, and this obs is in dict type
    """
    def __init__(self, env, **kwargs):
        super().__init__(env)

        # something useful 
        self.attribute_dict = self.backend_cfg.attribute_dict
        self.agent_count    = self.backend.agent_count
        self.agent_dict     = self.backend_cfg.agent_dict
        self.agent_list     = self.backend_cfg.agent_list
        self.name2typeid    = self.backend_cfg.name2typeid
        self.typeid2name    = self.backend_cfg.typeid2name
        self.item_dict      = self.backend_cfg.item_dict
        self.item_list      = self.backend_cfg.item_list
        self.being_list     = self.backend_cfg.being_list
        self.resource_list  = self.backend_cfg.resource_list
        # get every agent's type(name)
        self._agent_type()
        self.obs_dict = {}

    def reset(self, seed=0):
        o = self.env.reset(seed=seed)
        return o

    def step(self, action):
        o, r, d, i = self.env.step(action)
        return o, r, d, i

    def read(self):
        '''
        Read the original observation of agents.

        [Args]
            obs: the original observation of agents

        [Return]
            obs_dict: a dict of structural observation, every observation is in dict type

        [Example]
            >>> env = gym.make('eden-v0')
            >>> env = ObsReader(env)
            >>> env.reset()
            >>> env.read()
            >>> print(env.obs_dict['Brave'][0]['backpack'])
            {'Meat': -1, 'Water': -1, 'Ice': -1, 'Apple': -1, 'Torch': -1, 'Spear': -1, 'Bow': -1, 
            'LeatherArmor': -1, 'WoodArmor': -1, 'WarmStone': -1, 'ColdStone': -1, 'Cutgrass': -1, 
            'Stone': -1, 'Branch': -1, 'Leather': -1, 'GodWeapon': -1, 'Tendon': -1, 'Wood': -1, 
            'Hair': -1}
        '''
        obs = self.unwrapped.obs
        self._block_milestone(obs)

        self.obs_dict = {}
        for agent_typeid in self.agent_list:
            self.obs_dict[self.typeid2name[f'agent:{agent_typeid}']] = {}

        agent_id = 0
        for ob in obs:
            ob_dict = {}

            if isinstance(ob, np.ndarray):
                ob = ob.tolist()

            if len(ob) == 0:
                self.obs_dict[agent_id] = ob_dict
                agent_id += 1
                continue

            ob_dict['map']         = self._read_map(ob, agent_id)
            ob_dict['agent']       = self._read_agent(ob, agent_id)
            ob_dict['backpack']    = self._read_backpack(ob, agent_id)
            ob_dict['equipment']   = self._read_equipment(ob, agent_id)
            ob_dict['other_agent'] = self._read_other_agent(ob, agent_id)
            ob_dict['being']       = self._read_being(ob, agent_id)
            ob_dict['resource']    = self._read_resource(ob, agent_id)
            ob_dict['item']        = self._read_item(ob, agent_id)

            self.obs_dict[self.agent_type[agent_id]][agent_id] = ob_dict
            agent_id += 1

        return self.obs_dict


    def _agent_type(self):
        # get every agent's type(name), e.g 'Brave', 'PYS'
        last_index = 0
        self.agent_type = {}
        for key, value in self.agent_dict.items():
            same_type_agent_num = 0
            for distribution in value['Distribution'].split(';'):
                if distribution.split(':')[-1] != '':
                    same_type_agent_num += int(distribution.split(':')[-1])
            next_index = last_index + same_type_agent_num
            
            agent_id = last_index
            while agent_id >= last_index and agent_id < next_index:
                 self.agent_type[agent_id] = key
                 agent_id += 1
            
            last_index = next_index

    def _block_milestone(self, obs):
        if isinstance(obs,np.ndarray):
            obs = obs.tolist()
        self.block_milestone = {}
        agent_id = 0
        for ob in obs:
            block_milestone = {}
            
            if len(ob) == 0:
                self.block_milestone[agent_id] = block_milestone
                agent_id += 1
                continue
            
            Cursor = 0
            block_milestone['map'] = Cursor

            # part 1: basic infomation of env
            Cursor += 4
            block_milestone['agent'] = Cursor

            # part 2: basic infomation of agent
            Cursor += 2
            attr_num = round(ob[Cursor])
            Cursor += 1
            Cursor += attr_num
            block_milestone['backpack'] = Cursor

            # part 3: backpack and equipment
            backpack_num = round(ob[Cursor] * 2)
            Cursor += 1
            Cursor += backpack_num
            block_milestone['equipment'] = Cursor

            equipment_num = round(ob[Cursor])
            Cursor += 1
            Cursor += equipment_num
            block_milestone['other_agent'] = Cursor

            # part 4: other agent      
            agent_num = round(ob[Cursor] * 3)
            Cursor += 1
            Cursor += agent_num
            block_milestone['being'] = Cursor

            # part 5: being
            being_num = round(ob[Cursor] * 3)
            Cursor += 1
            Cursor += being_num
            block_milestone['resource'] = Cursor
            
            # part 6: resource
            resource_num = round(ob[Cursor] * 3)
            Cursor += 1
            Cursor += resource_num
            block_milestone['item'] = Cursor

            # part 7: item
            item_num = round(ob[Cursor] * 3)
            Cursor += 1
            Cursor += item_num
            assert Cursor == len(ob)

            self.block_milestone[agent_id] = block_milestone
            agent_id += 1
        assert agent_id == len(obs)

    def _read_map(self, ob, agent_id=0):
        map = {}
        Cursor = self.block_milestone[agent_id]['map']
        map['season']     = ob[Cursor]
        map['is_daytime'] = ob[Cursor + 1]
        map['weather']    = ob[Cursor + 2]
        map['landform']   = ob[Cursor + 3]
        return map
        
    def _read_agent(self, ob, agent_id=0):
        agent = {}
        Cursor = self.block_milestone[agent_id]['agent']

        agent['position'] = ob[Cursor : Cursor + 2]
        Cursor += 2
        Cursor += 1
        
        agent_type = self.agent_type[agent_id]
        keys = self.attribute_dict[int(self.name2typeid[agent_type].split(':')[-1])]
        for key in keys:
            agent[key] = ob[Cursor]
            Cursor += 1
        return agent

    def _read_backpack(self, ob, agent_id=0):
        backpack = {}
        for item_id in self.item_list:
            item_name = self.typeid2name[f'item:{round(item_id)}']
            backpack[item_name] = -1

        Cursor = self.block_milestone[agent_id]['backpack']
        backpack_num = round(ob[Cursor])
        Cursor += 1

        for i in range(backpack_num):
            if ob[Cursor] == -1.0:
                Cursor += 2
                continue
            item_name = self.typeid2name[f'item:{round(ob[Cursor])}']
            backpack[item_name] = ob[Cursor + 1]
            Cursor += 2
        return backpack

    def _read_equipment(self, ob, agent_id=0):
        equipment = {}
        agent_type = self.agent_type[agent_id]
        slot_list = self.agent_dict[agent_type]['Slot'].split(';')
        for slot in slot_list:
            # if slot is empty, then value is -1
            equipment[slot] = -1
        
        Cursor = self.block_milestone[agent_id]['equipment']
        equipment_num = round(ob[Cursor])
        Cursor += 1

        for i in range(equipment_num):
            if ob[Cursor] == -1.0:
                Cursor += 1
                continue
            equipment_name = self.typeid2name[f'item:{round(ob[Cursor])}']
            # maybe one equipment can be equip in multiple slots
            equipment_slot = self.item_dict[equipment_name]['Slot'].split(';')
            for slot in equipment_slot:
                equipment[slot] = ob[Cursor]
            Cursor += 1

        return equipment

    def _read_other_agent(self, ob, agent_id=0):
        other_agent = {}
        for item in self.agent_list:
            agent_name = self.typeid2name[f'agent:{item}']
            other_agent[agent_name] = []
        Cursor = self.block_milestone[agent_id]['other_agent']

        other_agent_num = round(ob[Cursor])
        Cursor += 1

        for i in range(other_agent_num):
            if ob[Cursor] == -1.0:
                Cursor += 3
                continue
            agent_name = self.typeid2name[f'agent:{round(ob[Cursor])}']
            distance = self.manhattan(ob[Cursor + 1: Cursor + 3], ob[4: 6])
            agent_posi = ob[Cursor + 1: Cursor + 3].copy()
            agent_posi.append(distance)
            other_agent[agent_name].append(agent_posi)
            Cursor += 3

        for key, value in other_agent.items():
            # For each agent in the field of vision, 
            # it is sorted from small to large according to its distance from the agent
            other_agent[key] = sorted(value, key=lambda t: t[-1])
        return other_agent

    def _read_being(self, ob, agent_id=0):
        being = {}
        for being_id in self.being_list:
            being_name = self.typeid2name[f'being:{round(being_id)}']
            being[being_name] = []

        Cursor = self.block_milestone[agent_id]['being']
        being_num = round(ob[Cursor])
        Cursor += 1

        for i in range(being_num):
            if ob[Cursor] == -1.0:
                Cursor += 3
                continue
            being_name = self.typeid2name[f'being:{round(ob[Cursor])}']
            distance = self.manhattan(ob[Cursor + 1: Cursor + 3], ob[4: 6])
            being_posi = ob[Cursor + 1: Cursor + 3].copy()
            being_posi.append(distance)
            being[being_name].append(being_posi)
            Cursor += 3

        for key, value in being.items():
            # For each being in the field of vision, 
            # it is sorted from small to large according to its distance from the agent
            being[key] = sorted(value, key=lambda t: t[-1])
        return being

    def _read_resource(self, ob, agent_id=0):
        resource = {}
        for resource_id in self.resource_list:
            resource_name = self.typeid2name[f'resource:{round(resource_id)}']
            resource[resource_name] = []

        Cursor = self.block_milestone[agent_id]['resource']
        resource_num = round(ob[Cursor])
        Cursor += 1

        for i in range(resource_num):
            if ob[Cursor] == -1.0:
                Cursor += 3
                continue
            resource_name = self.typeid2name[f'resource:{round(ob[Cursor])}']
            distance = self.manhattan(ob[Cursor + 1: Cursor + 3], ob[4: 6])
            resource_posi = ob[Cursor + 1: Cursor + 3].copy()
            resource_posi.append(distance)
            resource[resource_name].append(resource_posi)
            Cursor += 3

        for key, value in resource.items():
            # For each resource in the field of vision, 
            # it is sorted from small to large according to its distance from the agent
            resource[key] = sorted(value, key=lambda t: t[-1])
        return resource

    def _read_item(self, ob, agent_id=0):
        item = {}
        for item_id in self.item_list:
            item_name = self.typeid2name[f'item:{round(item_id)}']
            item[item_name] = []

        Cursor = self.block_milestone[agent_id]['item']
        item_num = round(ob[Cursor])
        Cursor += 1

        for i in range(item_num):
            if ob[Cursor] == -1.0:
                Cursor += 3
                continue
            item_name = self.typeid2name[f'item:{round(ob[Cursor])}']
            distance = self.manhattan(ob[Cursor + 1: Cursor + 3], ob[4: 6])
            item_posi = ob[Cursor + 1: Cursor + 3].copy()
            item_posi.append(distance)
            item[item_name].append(item_posi)
            Cursor += 3

        for key, value in item.items():
            # For each item in the field of vision, 
            # it is sorted from small to large according to its distance from the agent
            item[key] = sorted(value, key=lambda t: t[-1])
        return item


    def manhattan(self, A, B):
        return abs(A[0] - B[0]) + abs(A[1] - B[1])

if __name__ == '__main__':
    import gym, eden
    env = gym.make('eden-v0')
    env = ObsReader(env)
    env.reset()
    env.read()
    print(env.obs_dict)