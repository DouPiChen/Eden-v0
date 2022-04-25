'''class BackendInfo'''
#from _typeshed import ReadOnlyBuffer
import csv
import os
from typing import Dict, List


class BackendConfig:
    def __init__(self, config_dir='./config'):
        self.action_list = [
            'Idle','Attack','Collect','Pickup','Consume','Equip','Synthesize','Discard','Move'
        ]
        self.type_list = [
            'agent','being','item','resource','buff','weather','landform','attribute'
        ]
        self.load_csv_info(config_dir)

    def load_csv_info(self, config_dir):
        self._name2typeid = {}
        self._typeid2name = {}

        self._item_list = []
        self._agent_list = []
        self._being_list = []

        self._equip_list = []
        self._collect_list = []
        self._consume_list = []
        self._resource_list = []
        self._synthesis_list = []

        self._landform_list = []
        self._buff_list = []
        self._weather_list = []

        self.landform_dict = {}
        self.agent_dict = {}
        self.being_dict = {}
        self.item_dict = {}
        self.resource_dict = {}
        self.buff_dict = {}
        self.weather_dict = {}
        self.preset_dict = {}
        self.attribute_dict = {}

        self.general_dict  = self.read_csv(os.path.join(config_dir, '0_general.csv'))
        self.read_csv(os.path.join(config_dir, '1_landform.csv'))
        self.read_csv(os.path.join(config_dir, '2_agent.csv'))
        self.read_csv(os.path.join(config_dir, '3_being.csv'))
        self.read_csv(os.path.join(config_dir, '4_item.csv'))
        self.read_csv(os.path.join(config_dir, '5_resource.csv'))
        self.read_csv(os.path.join(config_dir, '6_buff.csv'))
        self.read_csv(os.path.join(config_dir, '7_weather.csv'))
        self.read_csv(os.path.join(config_dir, '8_preset.csv'))

    def read_csv(self, filename: str):
        csv_file = open(filename, encoding='utf-8-sig')
        csv_reader = csv.reader(csv_file)
        ret_dict = {}
        keys = []
        for i, row in enumerate(csv_reader):
            if i == 0:
                keys = row
            else:
                record = {}
                for key, value in zip(keys, row):
                    record[key] = value
                if 'general' in filename:
                    ret_dict = record.copy()
                elif 'agent' in filename:
                    self._agent_list.append(i - 1)
                    self._name2typeid[record['AgentName']] = f'agent:{i - 1}'
                    self._typeid2name[f'agent:{i - 1}'] = record['AgentName']
                    # attribute
                    name = record['AgentName']
                    self.agent_dict[name] = record.copy()
                    self.agent_dict[name]['Attribute'] = {}
                    attribute_names = []
                    for k, v in zip(list(record.keys())[3:14], list(record.values())[3:14]):
                        self.agent_dict[name]['Attribute'][k] = float(v)
                        attribute_names.append(k)
                    self.attribute_dict[i - 1] = attribute_names
                elif 'being' in filename:
                    self._being_list.append(i - 1)
                    self._name2typeid[record['BeingName']] = f'being:{i - 1}'
                    self._typeid2name[f'being:{i - 1}'] = record['BeingName']
                    # attribute
                    name = record['BeingName']
                    self.being_dict[name] = record.copy()
                    if record['CollectTable'] != '':
                        self._collect_list.append(f'being:{i - 1}')
                    self.being_dict[name]['Attribute'] = {}
                    for k, v in zip(list(record.keys())[1:10], list(record.values())[1:10]):
                        self.being_dict[name]['Attribute'][k] = float(v)
                elif 'item' in filename:
                    self._item_list.append(i - 1)
                    self._name2typeid[record['ItemName']] = f'item:{i - 1}'
                    self._typeid2name[f'item:{i - 1}'] = record['ItemName']
                    if record['ConsumeBuff'] != '':
                        self._consume_list.append(i - 1)
                    if record['Slot'] != '':
                        self._equip_list.append(f"{record['Slot']}:{i - 1}")
                    if record['SynthesizeTable'] != '':
                        self._synthesis_list.append(i - 1)
                    name = record['ItemName']
                    self.item_dict[name] = record.copy()
                    if record['SynthesizeTable'] != '':
                        self.item_dict[name]['SynthesizeTable'] = {}
                        for k_v in record['SynthesizeTable'].split(';'):
                            [k, v] = k_v.split(':')
                            self.item_dict[name]['SynthesizeTable'][k] = int(v)
                elif 'resource' in filename:
                    self._resource_list.append(i - 1)
                    self._name2typeid[record['ResourceName']] = f'resource:{i - 1}'
                    self._typeid2name[f'resource:{i - 1}'] = record['ResourceName']
                    if record['CollectTable'] != '':
                        self._collect_list.append(f'resource:{i - 1}')
                    name = record['ResourceName']
                    self.resource_dict[name] = record.copy()
                elif 'buff' in filename:
                    self._buff_list.append(i - 1)
                    name = record['BuffName']
                    self.buff_dict[name] = record.copy()
                    self.buff_dict[name]['Enhance']={}
                    for k_v in record['Enhance'].split(';'):
                        if len(k_v) < 1:
                            break
                        [k, v] = k_v.split(':')
                        self.buff_dict[name]['Enhance'][k] = float(v)
                elif 'weather' in filename:
                    self._weather_list = [idx for idx in range(1, len(keys))]
                    season_name = record['Season']
                    self.weather_dict[season_name] = record.copy()
                    if i == 1:
                        for weather_id, weather_name in enumerate(keys[1:]):
                            self._name2typeid[weather_name] = f'weather:{weather_id}'
                            self._typeid2name[f'weather:{weather_id}'] = weather_name
                elif 'landform' in filename:
                    self._landform_list.append(i - 1)
                    name = record['LandformName']
                    self._name2typeid[record['LandformName']] = f'landform:{i - 1}'
                    self._typeid2name[f'landform:{i - 1}'] = record['LandformName']
                    self.landform_dict[name] = record.copy()
        csv_file.close()
        return ret_dict

    @property
    def name2typeid(self) -> Dict[str, str]:
        '''
        agent, animal, plant, resource, item: name to typeid
        Key: name
        Value: Type,id
        '''
        return self._name2typeid

    @property
    def typeid2name(self) -> Dict[str, str]:
        '''
        agent, animal, plant, resource, item: typeid to name
        Key: Type,id
        Value: name
        '''
        return self._typeid2name

    @property
    def agent_list(self) -> List[int]:
        '''Agent_list: NameInt of all the agents'''
        return self._agent_list

    @property
    def being_list(self) -> List[int]:
        '''Being_list: NameInt of all the beings'''
        return self._being_list

    @property
    def item_list(self) -> List[int]:
        '''item_list: NameInt of all the items'''
        return self._item_list

    @property
    def resource_list(self) -> List[int]:
        '''resource_list: NameInt of all the resources'''
        return self._resource_list

    @property
    def synthesis_list(self) -> List[int]:
        '''
        Synthesis_list: NameInt of all the items in synthesise table, which means these items can be synthesized(action 6:Synthesize)
        '''
        return self._synthesis_list

    @property
    def collect_list(self) -> List[str]:
        '''
        Typeid of all the beings and resources have CollectTable
        '''
        return self._collect_list

    @property
    def consume_list(self) -> List[int]:
        '''
        consume_list: NameInt of all the items have ConsumeBuff
        '''
        return self._consume_list

    @property
    def equip_list(self) -> List[str]:
        '''
        equip_list: Slot-NameInt of all the items having EqiupBuff
        '''
        return self._equip_list

    @property
    def landform_list(self) -> List[int]:
        return self._landform_list

    @property
    def buff_list(self) -> List[int]:
        return self._buff_list

    @property
    def weather_list(self) -> List[int]:
        return self._weather_list


if __name__ == "__main__":
    cfg = BackendConfig()
    print(cfg.name2typeid)
    print(cfg.typeid2name)

    print(cfg.agent_list)
    print(cfg.being_list)

    print(cfg.synthesis_list)
    print(cfg.collect_list)
    print(cfg.consume_list)
    print(cfg.equip_list)

    print(cfg.agent_dict)
    print(cfg.being_dict)
    print(cfg.item_dict)
    print(cfg.buff_dict)
    print(cfg.weather_dict)
    print(cfg.landform_dict)
    print(cfg.resource_dict)
    print(cfg.attribute_dict)
