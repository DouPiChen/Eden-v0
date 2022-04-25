import os
import json
from gym import Wrapper

class Reward(Wrapper):
    def __init__(self, env, config_dir='./config'):
        super().__init__(env)
        score_filepath = os.path.join(config_dir, 'score.json')
        assert os.path.exists(score_filepath), f"{score_filepath} does not exist"
        self.reward_table = json.load(open(score_filepath, 'r'))
    
    def step(self,action):
        o, _, d, i = self.env.step(action)
        return o, self.reward(i), d, i

    def reward(self, info):
        rewards = []
        for action_result in info:
            # action
            reward = self.action_reward(action_result)
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

    def action_reward(self, action_result):
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
                    reward = result['default_' + action_result['result']]
                else:
                    reward = result[action_result['target']]
        return reward
