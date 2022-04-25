from gym import spaces
from gym import ObservationWrapper
import numpy as np

class ObsScale(ObservationWrapper):
    """
        Analyze observation protocol and scale
    """
    def __init__(self, env, n_target = 0, **kwargs):
        super().__init__(env)
        self.n_target = n_target
        
        self.item_IDs     = self.backend_cfg.item_list
        self.being_IDs    = self.backend_cfg.being_list
        self.resource_IDs = self.backend_cfg.resource_list
    
    def reset(self, seed=0):
        o = self.env.reset(seed=seed)
        obs_len = 0
        for single in o:
            single_obs_len = 6
            cursor = 6 # skip: season, daytime, weather, landform, x, y
            # attribute
            single_obs_len += int(single[cursor]) + 1
            cursor += int(single[cursor]) + 1
            # backpack
            single_obs_len += int(single[cursor]) * 2 + 1
            cursor += int(single[cursor]) * 2 + 1
            # equipment
            single_obs_len += int(single[cursor])
            # other agent, being, resource, item
            single_obs_len += 3 * 4
            obs_len = max(obs_len, single_obs_len)

        self.observation_space = spaces.Box(
            low=-10, 
            high=1000, 
            shape=(
                self.backend.agent_count,
                obs_len
            )
        )
        return o

    def observation(self, observation):
        return self._obs_scale(observation)
    
    def _obs_scale(self,observations):
        new_observations = []
        for obs in observations:
            new_observations.append(self._obs_scale_1d(obs))
        return np.array(new_observations)

    def _obs_scale_1d(self, observation):
        if len(observation) < 1:
            return np.array([])
        if isinstance(observation,np.ndarray):
            obs = observation.tolist()
        else:
            obs = observation
        obs_scaled = []
        Cursor = 0
        # part 1:basic infomation of env
        obs_scaled += obs[Cursor:Cursor+4]
        Cursor += 4

        # part 2: basic infomation of agent
        obs_scaled += obs[Cursor:Cursor+2] #position
        agent_posi = obs[Cursor:Cursor+2]
        Cursor += 2

        attr_num = round(obs[Cursor])
        Cursor += 1
        obs_scaled += obs[Cursor:Cursor+attr_num] #attribute
        Cursor += attr_num

        # part 3: backpack and equipment
        backpack_num = round(obs[Cursor] * 2)
        Cursor += 1
        obs_scaled += obs[Cursor:Cursor+backpack_num] #backpack
        Cursor += backpack_num

        equipment_num = round(obs[Cursor])
        Cursor += 1
        obs_scaled += obs[Cursor:Cursor+equipment_num] #equipment
        Cursor += equipment_num

        # part 4: find nearest agent,being,resource       
        agent_num = round(obs[Cursor] * 3)
        Cursor += 1
        obs_scaled += self.find_nearest(agent_posi,obs[Cursor:Cursor+agent_num]) #agent
        Cursor += agent_num

        being_num = round(obs[Cursor] * 3)
        Cursor += 1
        obs_scaled += self.find_nearest(agent_posi,obs[Cursor:Cursor+being_num],self.being_IDs) #being
        Cursor += being_num

        resource_num = round(obs[Cursor] * 3)
        Cursor += 1
        obs_scaled += self.find_nearest(agent_posi,obs[Cursor:Cursor+resource_num],self.resource_IDs) #resource
        Cursor += resource_num

        item_num = round(obs[Cursor] * 3)
        Cursor += 1
        obs_scaled += self.find_nearest(agent_posi,obs[Cursor:Cursor+item_num],self.item_IDs) #item
        Cursor += item_num

        assert Cursor == len(obs)
        return np.array(obs_scaled)

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
            for key in IDs:
                if key in id.keys():
                    print(f"[Warning in obs_scale] there is two same id")
                    continue                    
                id[key] = [-1,-1] #[minIndex,minDistance]
            for i in range(0,len(obs_slice),3):
                distance = self.manhattan(agent_posi,obs_slice[i+1:i+3])
                nameInt = round(obs_slice[i])
                if nameInt in id.keys():
                    if id[nameInt][1] == -1 or distance < id[nameInt][1]:
                        id[nameInt][0] = i
                        id[nameInt][1] = distance
            new_obs_slice = []
            for key in IDs:
                minIndex = id[key][0]
                if minIndex != -1:
                    new_obs_slice += obs_slice[minIndex:minIndex+3]
                else:
                    new_obs_slice += [-1,-1,-1]
            return new_obs_slice         

        else:
            print(f"[ERROR in obs_scale] IDs should be a list, but it's a {type(IDs)}") #just in case
            return []

    def manhattan(self, A, B):
        return abs(A[0] - B[0]) + abs(A[1] - B[1])

if __name__ == '__main__':
    import gym, eden
    env = gym.make('eden-v0')
    env = ObsScale(env)
    print(env.reset().shape)