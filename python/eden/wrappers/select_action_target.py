from gym import spaces
from gym import ActionWrapper
import numpy as np
import random

class SelectActionTarget(ActionWrapper):
    """
        select nearest target
    """
    def __init__(self, env, **kwargs):
        super().__init__(env)

        ##各个动作会指定的目标
        self.attack_target  = [0] 
        self.collect_list   = self.backend_cfg.collect_list     # ['being:1', 'resource:2']
        self.pickup_list    = self.backend_cfg.item_list        # [3,5,10,11,0]
        self.consume_list   = self.backend_cfg.consume_list     # [10,11,0]
        self.equip_list     = self.backend_cfg.equip_list       # ['Weapon:3', 'Weapon:5', 'Other:0']
        self.synthesis_list = self.backend_cfg.synthesis_list   # [5]
        self.discard_list   = self.pickup_list

        ##其他需要的参数
        self.being_list = self.backend_cfg.being_list
        self.resource_list = self.backend_cfg.resource_list
        self.item_list = self.backend_cfg.item_list
        self.slot_name = list(self.backend_cfg.agent_dict.values())[0]['Slot'].split(';') # ['Weapon','Armor','Other']
        self.slot_dist = {}
        for i in range(len(self.slot_name)):
            self.slot_dist[self.slot_name[i]] = i

        self.collect_dist = {'being':{}, 'resource':{}} # {'being': {1: [3]}, 'resource': {2: [11]}}
        for i in range(len(self.collect_list)):
            kind,id = self.collect_list[i].split(':')
            id = int(id)
            name = self.backend_cfg.typeid2name[self.collect_list[i]]
            if kind == 'being':
                table = self.backend_cfg.being_dict[name]['CollectTable'].split(';')  #['Branch:10:2']
            else:
                table = self.backend_cfg.resource_dict[name]['CollectTable'].split(';')
            self.collect_dist[kind][id] = []
            for t in table:
                drop_name = t.split(':')[0]
                drop_id = int(self.backend_cfg.name2typeid[drop_name].split(':')[1])
                self.collect_dist[kind][id].append(drop_id)

        self.pig_id   = int(self.backend_cfg.name2typeid['Pig'].split(':')[1])
        self.meat_id  = int(self.backend_cfg.name2typeid['Meat'].split(':')[1])
        self.water_id = int(self.backend_cfg.name2typeid['Water'].split(':')[1])
        self.torch_id = int(self.backend_cfg.name2typeid['Torch'].split(':')[1])
        self.pool_id  = int(self.backend_cfg.name2typeid['Pool'].split(':')[1])

        #action config
        self.ACTION_IDLE       = 0
        self.ACTION_ATTACK     = 1
        self.ACTION_COLLECT    = 2
        self.ACTION_PICKUP     = 3
        self.ACTION_CONSUME    = 4
        self.ACTION_EQUIP      = 5
        self.ACTION_SYNTHESIZE = 6
        self.ACTION_DISCARD    = 7
        self.ACTION_MOVE       = 8

        # obs analyse setting
        self.BLOCK_POSISION  = 0
        self.BLOCK_ATTRIBUTE = 1
        self.BLOCK_BACKPACK  = 2
        self.BLOCK_EQUIPMENT = 3
        self.BLOCK_AGENT     = 4
        self.BLOCK_BEING     = 5
        self.BLOCK_RESOURCE  = 6
        self.BLOCK_ITEM      = 7
        self.BlOCK_ENV       = 8
    
    def reset(self, seed=0):
        #action_space setting
        self.action_space = spaces.MultiDiscrete([len(self.backend_cfg.action_list)] * self.backend.agent_count)
        return self.env.reset(seed)

    def action(self, action):
        new_actions = []
        observations = self.unwrapped.obs
        assert(len(observations)==len(action)), "action is the same length with observations"
        for i in range(len(action)):
            new_actions.append(self.target_function(action[i], observations[i]))
        return np.array(new_actions)
        
    def target_function(self, action, obs):
        # dead
        if len(obs) < 1:
            return [self.ACTION_IDLE, 0, 0]
        #0、idle
        if action == self.ACTION_IDLE:
            return [self.ACTION_IDLE,0,0]

        #1、攻击pig
        elif action == self.ACTION_ATTACK:
            block_list = [self.BLOCK_BEING]
            [beings] = self.find_block(obs, block_list) #like {0: [5.0, 4.0], 1: [4.0, 5.0]}

            posi = beings[self.pig_id]

            return [self.ACTION_ATTACK] + posi
            
        #2、尽可能采集背包里少的东西
        elif action == self.ACTION_COLLECT:
            block_list = [self.BLOCK_BACKPACK, self.BLOCK_BEING, self.BLOCK_RESOURCE, self.BLOCK_ATTRIBUTE, self.BLOCK_POSISION]
            [backpack, beings, resource, attribute, agent_posi] = self.find_block(obs, block_list)
            collectDistance = attribute[7]
            candidate = []
            collect_list = self.collect_list[:]
            random.shuffle(collect_list)
            for kindAndID in collect_list:
                kind,id = kindAndID.split(':')
                id = int(id)
                if kind == 'being':
                    posi = beings[id]
                elif kind == 'resource':
                    posi = resource[id]
                else:
                    posi = [-1,-1]
                    print(f'[warning at selectActionTarget.py:target_function:collect] unknown kind `{kind}` in collect list')
                
                if posi[0] == -1 and self.manhattan(posi,agent_posi) > collectDistance:
                    continue
                for itemId in self.collect_dist[kind][id]:
                    if backpack[itemId] < 2:     
                        return [self.ACTION_COLLECT] + posi #如果某种item较少，直接采集
                candidate.append(posi) #否则加入候选
                
            if len(candidate) == 0:
                return [self.ACTION_COLLECT,-1,-1]
            else:
                r = random.randint(0,len(candidate)-1)
                return [self.ACTION_COLLECT] + candidate[r]

        #3、pickup 尽可能捡起背包里没有的东西
        elif action == self.ACTION_PICKUP:
            block_list = [self.BLOCK_BACKPACK, self.BLOCK_ITEM]
            [backpack, items] = self.find_block(obs, block_list)
            candidate = []
            pickup_list = self.pickup_list[:]
            random.shuffle(pickup_list)
            for itemId in pickup_list:
                if items[itemId][0] == -1 and items[itemId][1] == -1: #没有观测到此物品
                    continue
                if backpack[itemId] < 1:     
                    return [self.ACTION_PICKUP] + items[itemId] #如果没用某种item，直接pickup
                candidate.append(items[itemId]) #否则加入候选
            if len(candidate) == 0:
                return [self.ACTION_PICKUP, -1, -1]
            else:
                r = random.randint(0,len(candidate)-1)
                return [self.ACTION_PICKUP] + candidate[r]

        #4、consume
        elif action == self.ACTION_CONSUME:
            block_list = [self.BLOCK_ATTRIBUTE, self.BLOCK_BACKPACK]
            [attribute, backpack] = self.find_block(obs, block_list)
            candidate = []
            satiety = attribute[1]
            thirsty = attribute[2]

            #只吃肉和水,只吃1个
            for itemId in self.consume_list:
                if backpack[itemId] <= 0:
                    continue
                if itemId == self.meat_id:
                    if satiety < thirsty:
                        return [self.ACTION_CONSUME,itemId,1]
                elif itemId == self.water_id:
                    if satiety >= thirsty:
                        return [self.ACTION_CONSUME,itemId,1]
                else:
                    continue
                candidate.append([itemId,1])

            if len(candidate) == 0:
                return [self.ACTION_CONSUME, -1, -1] #吃个不存在的肉
            else:
                r = random.randint(0,len(candidate)-1)
                return [self.ACTION_CONSUME] + candidate[r]

        #5、equip
        elif action == self.ACTION_EQUIP:
            block_list = [self.BLOCK_BACKPACK, self.BLOCK_EQUIPMENT]
            [backpack, equipment] = self.find_block(obs, block_list)
            candidate = []

            for kindAndID in self.equip_list:
                kind,id = kindAndID.split(':')
                id = int(id)
                if backpack[id] <= 0 or id == equipment[self.slot_dist[kind]]: #物品不存在 or 这个类型的slot上已装备同种物品
                    continue
                candidate.append([id, -1]) #param2没有用
            
            default_value = [self.ACTION_EQUIP, -1, -1]
            if len(candidate) > 0:
                r = random.randint(0,len(candidate)-1)
                return [self.ACTION_EQUIP] + candidate[r]
            return default_value

        #6、synthesize 只有火把
        elif action == self.ACTION_SYNTHESIZE:
            return [self.ACTION_SYNTHESIZE,self.torch_id,1]

        #7、discard 随机丢掉背包里有的东西
        elif action == self.ACTION_DISCARD:
            block_list = [self.BLOCK_BACKPACK]
            [backpack] = self.find_block(obs, block_list)
            candidate = []

            for itemId in self.item_list:
                if backpack[itemId] <= 0:
                    continue
                candidate.append([itemId, -1]) #param2没有用

            default_value = [self.ACTION_DISCARD, -1, -1]
            if len(candidate) > 0:
                r = random.randint(0,len(candidate)-1)
                return [self.ACTION_DISCARD] + candidate[r]
            return default_value

        #8、move 饿了找pig、渴了找pool、否则随机，有其他的需求再改
        elif action == self.ACTION_MOVE:
            block_list = [self.BLOCK_POSISION,self.BLOCK_ATTRIBUTE, self.BLOCK_BEING, self.BLOCK_RESOURCE]
            [agent_posi, attribute, beings, resource] = self.find_block(obs, block_list)
            candidate = []
            satiety = attribute[1]
            thirsty = attribute[2]
            speed = attribute[10]
            pig_posi = beings[self.pig_id]
            pool_posi = resource[self.pool_id]

            if pig_posi[0] != -1: 
                target = self.check_move_target(agent_posi, pig_posi, speed)
                if satiety < thirsty:
                    return [self.ACTION_MOVE] + target
                candidate.append(target)

            if pool_posi[0] != -1:
                target = self.check_move_target(agent_posi, pool_posi, speed)
                if thirsty > satiety:
                    return [self.ACTION_MOVE] + target
                candidate.append(target)

            if len(candidate) == 0: #randon move
                target = agent_posi
                x = random.randint(-0.5*speed,0.5*speed)
                rest_speed = 0.5 * speed - abs(x)
                y = random.randint(-rest_speed,rest_speed)
                target[0] += x
                target[1] += y
                return [self.ACTION_MOVE] + target
            else:
                r = random.randint(0,len(candidate)-1)
                return [self.ACTION_MOVE] + candidate[r]

        else:
            raise Warning(f'there isnt action id {action}.')
        return [self.ACTION_IDLE,0,0]
    
    def find_block(self, observation, block_index = [0]):
        '''
            get infomation of block needed
        '''
        if isinstance(observation,np.ndarray):
            obs = observation.tolist()
        else:
            obs = observation

        Blocks = {}
        Cursor = 0

        if self.BlOCK_ENV in block_index:
            Blocks[self.BlOCK_ENV] = obs[Cursor:Cursor+4]
        Cursor += 4

        if self.BLOCK_POSISION in block_index:
            Blocks[self.BLOCK_POSISION] = obs[Cursor:Cursor+2] #position
        Cursor += 2

        attr_num = round(obs[Cursor])
        Cursor += 1
        if self.BLOCK_ATTRIBUTE in block_index:
            Blocks[self.BLOCK_ATTRIBUTE] = obs[Cursor:Cursor+attr_num] #attribute
        Cursor += attr_num

        backpack_num = round(obs[Cursor] * 2)
        Cursor += 1
        if self.BLOCK_BACKPACK in block_index:
            Blocks[self.BLOCK_BACKPACK] = self.analyse_backpack(obs[Cursor:Cursor+backpack_num]) #backpack各种item数量的字典
        Cursor += backpack_num

        equipment_num = round(obs[Cursor])
        Cursor += 1
        if self.BLOCK_EQUIPMENT in block_index:
            Blocks[self.BLOCK_EQUIPMENT] = obs[Cursor:Cursor+equipment_num] #equipment
        Cursor += equipment_num
        
        #part3 使用find_near去返回{id:位置}的字典, (除了agent)
        agent_num = round(obs[Cursor] * 3)
        Cursor += 1
        if self.BLOCK_AGENT in block_index:
            Blocks[self.BLOCK_AGENT] = self.find_nearest(obs[0:2],obs[Cursor:Cursor+agent_num]) #agent
        Cursor += agent_num

        being_num = round(obs[Cursor] * 3)
        Cursor += 1
        if self.BLOCK_BEING in block_index:
            Blocks[self.BLOCK_BEING] = self.find_nearest(obs[0:2],obs[Cursor:Cursor+being_num],self.being_list) #being
        Cursor += being_num

        resource_num = round(obs[Cursor] * 3)
        Cursor += 1
        if self.BLOCK_RESOURCE in block_index:
            Blocks[self.BLOCK_RESOURCE] = self.find_nearest(obs[0:2],obs[Cursor:Cursor+resource_num],self.resource_list) #resource
        Cursor += resource_num

        item_num = round(obs[Cursor] * 3)
        Cursor += 1
        if self.BLOCK_ITEM in block_index:
            Blocks[self.BLOCK_ITEM] = self.find_nearest(obs[0:2],obs[Cursor:Cursor+item_num],self.item_list) #item
        Cursor += item_num

        return [Blocks[id] for id in block_index]

    def find_nearest(self, agent_posi, obs_slice, IDs = None):
        if IDs is None: #agent
            if len(obs_slice) == 0:
                return [-1,-1,-1]
            if len(obs_slice) == 3:
                return obs_slice

            assert len(obs_slice) % 3 == 0
            minIndex = 0
            minDistance = -1
            for i in range(0,len(obs_slice),3):
                distance = self.manhattan(agent_posi,obs_slice[i+1:i+3])
                if minDistance == -1 or distance < minDistance:
                    minIndex = i
                    minDistance = distance
            return obs_slice[minIndex:minIndex+3]
            
        elif isinstance(IDs,list): #being & resource
            id = {}
            for i in IDs:
                if i in id.keys():
                    print(f"[Warning in obs_scale] there is two same id")
                    continue                    
                id[i] = [-1,-1] #[minIndex,minDistance]
            for i in range(0,len(obs_slice),3):
                distance = self.manhattan(agent_posi,obs_slice[i+1:i+3])
                nameInt = round(obs_slice[i])
                if nameInt in id.keys():
                    if id[nameInt][1] == -1 or distance < id[nameInt][1]:
                        id[nameInt][0] = i
                        id[nameInt][1] = distance
            obs_dist = {}
            for key in id.keys():
                minIndex = id[key][0]
                if minIndex != -1:
                    #assert(obs_slice[minIndex] == key)
                    obs_dist[key] = obs_slice[minIndex+1:minIndex+3]
                else:
                    obs_dist[key] = [-1,-1]
            return obs_dist         

        else:
            print(f"[ERROR in obs_scale] IDs should be a list, but it's a {type(IDs)}") #just in case
            return []

    def manhattan(self, A, B):
        return abs(A[0] - B[0]) + abs(A[1] - B[1])
    
    def analyse_backpack(self, backpack):
        '''
            count the number of every kind of item
            return: dist
        '''
        result = {}
        for i in self.item_list:
            result[i] = 0
        for i in range(0,len(backpack),2):
            nameInt = round(backpack[i])
            if (nameInt != -1) and nameInt in result.keys():
                result[nameInt] += backpack[i+1]
        return result
    
    def check_move_target(self,agent_posi,target_posi,speed):
        distance = self.manhattan(agent_posi,target_posi)
        if distance > speed:
            target = [0,0]
            target[0] = agent_posi[0] + int( (target_posi[0] - agent_posi[0]) * speed / distance)
            target[1] = agent_posi[1] + int( (target_posi[1] - agent_posi[1]) * speed / distance)
        else:
            target = target_posi
        return target