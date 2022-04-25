#!/usr/bin/env python
import os
from posixpath import split
import pygame
import numpy as np
from eden.core import Eden
import platform
if platform.system() == 'Windows':
    import ctypes
    ctypes.windll.user32.SetProcessDPIAware()
from pygame.transform import scale as surf_scale
from typing import List, Tuple

asset_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'assets')

FONT = os.path.join(asset_dir, 'consola.ttf')
FONT_SIZE = 16
FONT_WHITE = (255, 255, 255)
FONT_BLACK = (0, 0, 0)
FONT_RED   = (200, 0, 0)
FONT_GREEN = (0, 200, 0)
FONT_BLUE  = (0, 0, 200)

PIC_SIZE= 32

BLOCK_BORDER     = 0
BLOCK_SYNTHESIZE = 1
BLOCK_BACKPACK   = 2
BLOCK_EQUIPMENT  = 3
BLOCK_MAP        = 4
BLOCK_ATTRIBUTE  = 5

BLOCK_ASSET_NAME = {
    BLOCK_BORDER:     'border', 
    BLOCK_SYNTHESIZE: 'synthesize', 
    BLOCK_BACKPACK:   'slot_bp', 
    BLOCK_EQUIPMENT:  'slot_eq', 
    BLOCK_MAP:        'background', 
    BLOCK_ATTRIBUTE:  'background'
}
FOG_ASSET_NAME = ['fog_black', 'fog_white']
TYPE_NAME = ["agent", "being", "item", "resource", "buff", "weather", "landform", "attribute"]

ACTION_IDLE       = 0
ACTION_ATTACK     = 1
ACTION_COLLECT    = 2
ACTION_PICKUP     = 3
ACTION_CONSUME    = 4
ACTION_EQUIP      = 5
ACTION_SYNTHESIZE = 6
ACTION_DISCARD    = 7
ACTION_MOVE       = 8

class Render:
    def __init__(self, env:Eden, display_size:int=20) -> None:
        assert display_size >= 16, "display_size is supposed to be >= 16"
        self.env = env
        self.n_agent = env.backend.agent_count
        self.current_agent = 0
        self.action = [[]] * self.n_agent

        self.display_size = display_size
        self.info_linewidth = display_size - 7
        self.backpack_line_n   = int(np.ceil(self.env.backpack_size / 10))
        self.equipment_line_n  = int(np.ceil(self.env.equipment_size / 10))
        self.synthesize_line_n = int(np.ceil(len(self.env.synthesize_list) / 10))
        self.attribute_line_n  = int(np.ceil(len(env.attribute_name) / 2))

        self.window_x = int(1 + self.display_size + 1 + 10 + 1) # border map border slot border
        self.window_y = int(1 + self.display_size + 1 + 6  + 1) # border map border info border
        self.window_y = max(
            self.window_y,
            1 + self.backpack_line_n +     # backpack
            1 + self.equipment_line_n +    # equipment
            1 + self.synthesize_line_n + 1 # synthesize
        )

        self.is_daytime = True
        self.current_vision_range = 0
        self.ui_info = None
        self.assets = {}
        self.block_size = PIC_SIZE
        self.block = np.zeros((self.window_x, self.window_y), dtype=int) # record block_type of every block
        self.nameint = np.zeros_like(self.block, dtype=int) - 1          # used in click support for [backpack, equipment, synthesize]
        self.mouse_info = ""
        self.block_x = -1
        self.block_y = -1
        self._init_display()
        
    def ui_run(self):
        while self.fresh():
            self.clock.tick(15)
        pygame.quit()
    
    def fresh(self) -> bool:
        '''
        Fresh the ui. Return False if ui window is closed else True
        '''
        self._draw_ui()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            elif event.type == pygame.MOUSEBUTTONDOWN:
                action = self._handle_mouse_click(event)
                if len(action) > 0:
                    self.action[self.current_agent] = action
                    self.current_agent += 1
                    if self.current_agent >= self.n_agent:
                        self.current_agent = 0
                        self.env.step(self.action)
            elif event.type == pygame.MOUSEMOTION:
                self._handle_mouse_motion(event)
            elif event.type == pygame.VIDEORESIZE:
                self.block_size = np.floor(min(event.w / self.window_x, event.h / self.window_y))
                self.font = pygame.font.Font(FONT, int(self.block_size // 2))
                self.attr_font = pygame.font.Font(FONT, int(self.block_size // 4))
        return True
    
    def _draw_ui(self):
        self.ui_info = self.env.backend.ui(self.current_agent)
        self._draw_border()
        self._draw_info()
        self._draw_synthesize_list()
        cursor = self._draw_map()
        cursor = self._draw_attribute(cursor)
        cursor = self._draw_backpack(cursor)
        cursor = self._draw_equipment(cursor)
        pygame.display.flip()

    def _handle_mouse_motion(self, event):
        cursor_x, cursor_y = pygame.mouse.get_pos()
        self.block_x = int(cursor_x // self.block_size)
        self.block_y = int(cursor_y // self.block_size)
        # mouse info
        x = self.block_x
        y = self.block_y
        if x < 0 or x >= self.window_x:
            return []
        if y < 0 or y >= self.window_y:
            return []
        target_0, target_1 = self._get_target_param()
        if self.block[x, y] == BLOCK_MAP:
            cursor = 1 + (target_0 * self.env.map_size_x + target_1) * 6
            if self.ui_info[cursor + 1] < 0: # not occupied, record lanform name
                self.mouse_info = self.env.run_script(f"get.landform.{target_0}-{target_1}")
            else: # occupied, record object info
                self.mouse_info = self.env.run_script(f"get.map.{target_0}-{target_1}|get.info.$0")
        elif self.block[x, y] == BLOCK_BACKPACK:
            row = y - 1
            col = x - 2 - self.display_size
            slot = row * 10 + col
            name_id = self.env.run_script(f"get.agent.{self.current_agent}|get.backpack.$0.{slot}")
            if name_id != "":
                self.mouse_info = self.env.run_script(f"get.info.{name_id}")
            else:
                self.mouse_info = "Empty Backpack Slot"
        elif self.block[x, y] == BLOCK_EQUIPMENT:
            row = y - 2 - self.backpack_line_n
            col = x - 2 - self.display_size
            slot = row * 10 + col
            name_id = self.env.run_script(f"get.agent.{self.current_agent}|get.equipment.$0.{slot}")
            if name_id != "":
                self.mouse_info = self.env.run_script(f"get.info.{name_id}")
            else:
                self.mouse_info = "Empty Equipment Slot"
        elif self.block[x, y] == BLOCK_SYNTHESIZE:
            row = y - 3 - self.backpack_line_n - self.equipment_line_n
            col = x - 2 - self.display_size
            slot = row * 10 + col
            name = self.env.backend_cfg.typeid2name[f"item:{self.nameint[x, y]}"]
            self.mouse_info = f"[{name}] " + self.env.run_script(f"get.synthesize_table.{name}")

    def _handle_mouse_click(self, event) -> List[float]:
        if event.button not in [pygame.BUTTON_LEFT, pygame.BUTTON_RIGHT]:
            return []
        x = self.block_x
        y = self.block_y
        if x < 0 or x >= self.window_x:
            return []
        if y < 0 or y >= self.window_y:
            return []
        target_0, target_1 = self._get_target_param()
        if self.block[x, y] == BLOCK_MAP:
            cursor = 1 + (target_0 * self.env.map_size_x + target_1) * 6
            if self.ui_info[cursor + 1] < 0: # not occupied, move here
                return [ACTION_MOVE, target_0, target_1]
            else: # occupied, take action accordingly
                type_name = TYPE_NAME[int(self.ui_info[cursor + 1])]
                if type_name == 'agent':
                    return [ACTION_IDLE, -1, -1]
                elif type_name == 'being':
                    return [
                        ACTION_COLLECT if event.button == pygame.BUTTON_LEFT else ACTION_ATTACK,
                        target_0, target_1
                    ]
                elif type_name == 'resource':
                    return [ACTION_COLLECT, target_0, target_1]
                elif type_name == 'item':
                    return [ACTION_PICKUP, target_0, target_1]
        elif self.block[x, y] == BLOCK_BACKPACK:
            if self.nameint[x, y] < 0: # empty, return
                return []
            if event.button == pygame.BUTTON_RIGHT:
                return [ACTION_DISCARD, target_0, target_1]
            if self.nameint[x, y] in [int(x.split(':')[-1]) for x in self.env.backend_cfg.equip_list]:
                return [ACTION_EQUIP, target_0, target_1]
            elif self.nameint[x, y] in self.env.backend_cfg.consume_list:
                return [ACTION_CONSUME, target_0, target_1]
        elif self.block[x, y] == BLOCK_EQUIPMENT:
            if self.nameint[x, y] < 0: # empty, return
                return []
            return [ACTION_EQUIP, target_0, target_1]
        elif self.block[x, y] == BLOCK_SYNTHESIZE:
            return [ACTION_SYNTHESIZE, target_0, target_1]
        return []

    def _get_target_param(self):
        target_0 = -1
        target_1 = -1
        x = self.block_x
        y = self.block_y
        if self.block[x, y] == BLOCK_SYNTHESIZE:
            target_0 = self.nameint[x, y]
            target_1 = 1
        elif self.block[x, y] == BLOCK_BACKPACK:
            target_0 = self.nameint[x, y]
            target_1 = 1
        elif self.block[x, y] == BLOCK_EQUIPMENT:
            # equipment
            target_0 = self.nameint[x, y]
            target_1 = 1
        elif self.block[x, y] == BLOCK_MAP:
            # map
            lt_x, lt_y = self._get_display_rect()
            target_0 = x - 1 + lt_x
            target_1 = y - 1 + lt_y
        return int(target_0), int(target_1)

    def _init_display(self):
        pygame.init()
        self.screen = pygame.display.set_mode(
            (self.window_x * PIC_SIZE, self.window_y * PIC_SIZE),
            pygame.RESIZABLE
        )
        self.clock = pygame.time.Clock()
        self.font      = pygame.font.Font(FONT, int(self.block_size // 2))
        self.attr_font = pygame.font.Font(FONT, int(self.block_size // 4))
        self._init_assets()
        self._init_block()
        for name in BLOCK_ASSET_NAME.values():
            assert name in self.assets.keys(), "Could not find {name} in assets"
        for name in FOG_ASSET_NAME:
            assert name in self.assets.keys(), "Could not find {name} in assets"

    def _init_assets(self):
        for file in os.listdir(asset_dir):
            if '.png' != file[-4:]:
                continue
            surf = pygame.image.load(os.path.join(asset_dir, file)).convert_alpha()
            self.assets[file[:-4]] = surf

    def _init_block(self):
        # map
        for x in range(1, 1 + self.display_size):
            for y in range(1, 1 + self.display_size):
                self.block[x, y] = BLOCK_MAP
        # attribute
        for x in range(1, 1 + 6):
            for y in range(2 + self.display_size, self.window_y - 1):
                self.block[x, y] = BLOCK_ATTRIBUTE
        # info
        shift_x = 8
        for y in range(2 + self.display_size, self.window_y - 1):
            for x in range(8, 1 + self.display_size):
                self.block[x, y] = BLOCK_ATTRIBUTE
        # backpack
        shift_x = 2 + self.display_size
        shift_y = 1
        for i in range(self.env.backpack_size):
            y = int(i // 10)
            x = i - y * 10
            self.block[x + shift_x, y + shift_y] = BLOCK_BACKPACK
        # equipment
        shift_y += self.backpack_line_n + 1
        for i in range(self.env.equipment_size):
            y = int(i // 10)
            x = i - y * 10
            self.block[x + shift_x, y + shift_y] = BLOCK_EQUIPMENT
        # synthesize list
        shift_y += self.equipment_line_n + 1
        for i in range(len(self.env.synthesize_list)):
            y = int(i // 10)
            x = i - y * 10
            self.block[x + shift_x, y + shift_y] = BLOCK_SYNTHESIZE

    def _draw_border(self):
        for x in range(self.window_x):
            for y in range(self.window_y):
                name = BLOCK_ASSET_NAME[self.block[x, y]]
                self.screen.blit(
                    surf_scale(self._get_asset(name), [self.block_size] * 2),
                    (x * self.block_size, y * self.block_size)
                )

    def _draw_map(self):
        lt_x, lt_y = self._get_display_rect()
        # weather
        weather_id = int(self.ui_info[0])
        weather_name = self.env.backend_cfg.typeid2name[f"weather:{weather_id}"]
        # map
        self.screen.blit(
            self.font.render("(X)".center(4), True, FONT_WHITE),
            ((1 + min(self.display_size, self.env.map_size_x)) * self.block_size, int(0.25 * self.block_size))
        )
        self.screen.blit(
            self.font.render("(Y)".center(4), True, FONT_WHITE),
            (0, (1 + min(self.display_size, self.env.map_size_y)) * self.block_size)
        )
        cursor = 1
        for x in range(self.env.map_size_x):
            for y in range(self.env.map_size_y):
                block_x = x - lt_x
                block_y = y - lt_y
                if block_x >=0 and block_y >= 0 and block_x < self.display_size and block_y < self.display_size:
                    if block_x == 0:
                        self.screen.blit(
                            self.font.render(str(y).center(4), True, FONT_WHITE),
                            (0, int((1.25 + block_y) * self.block_size))
                        )
                    if block_y == 0:
                        self.screen.blit(
                            self.font.render(str(x).center(4), True, FONT_WHITE),
                            ((1 + block_x) * self.block_size, int(0.25 * self.block_size))
                        )
                    name = self.env.backend_cfg.typeid2name[f"landform:{int(self.ui_info[cursor])}"]
                    self.screen.blit(
                        surf_scale(self._get_asset(name), [self.block_size] * 2),
                        ((1 + block_x) * self.block_size, (1 + block_y) * self.block_size)
                    )
                    self.screen.blit(
                        surf_scale(self.assets[weather_name], [self.block_size] * 2),
                        ((1 + block_x) * self.block_size, (1 + block_y) * self.block_size)
                    )
                    if int(self.ui_info[cursor+1]) >= 0:
                        type_name = TYPE_NAME[int(self.ui_info[cursor+1])]
                        name = self.env.backend_cfg.typeid2name[
                            f"{type_name}:{int(self.ui_info[cursor+2])}"
                        ]
                        self.screen.blit(
                            surf_scale(self._get_asset(name), [self.block_size] * 2),
                            ((1 + block_x) * self.block_size, (1 + block_y) * self.block_size)
                        )
                        # if type_name == 'agent':
                        #     self.screen.blit(
                        #         self.attr_font.render(f"{int(self.ui_info[cursor+3])}".center(5), True, FONT_WHITE, FONT_RED),
                        #         (int((1.125 + block_x) * self.block_size), (1 + block_y) * self.block_size)
                        #     )
                        #     self.screen.blit(
                        #         self.attr_font.render(f"{int(self.ui_info[cursor+4])}".center(3), True, FONT_WHITE, FONT_GREEN),
                        #         ((1 + block_x) * self.block_size, int((1.75 + block_y) * self.block_size))
                        #     )
                        #     self.screen.blit(
                        #         self.attr_font.render(f"{int(self.ui_info[cursor+5])}".center(3), True, FONT_WHITE, FONT_BLUE),
                        #         (int((1.5 + block_x) * self.block_size), int((1.75 + block_y) * self.block_size))
                        #     )
                        # elif type_name == 'being':
                        #     self.screen.blit(
                        #         self.attr_font.render(f"{int(self.ui_info[cursor+3])}".center(5), True, FONT_WHITE, FONT_RED),
                        #         (int((1.125 + block_x) * self.block_size), (1 + block_y) * self.block_size)
                        #     )
                cursor += 6
        # is daytime
        self.is_daytime = (self.ui_info[cursor] > 1e-4)
        cursor += 1
        # position
        agent_x = int(self.ui_info[cursor])
        agent_y = int(self.ui_info[cursor+1])
        # fog
        for x in range(self.env.map_size_x):
            for y in range(self.env.map_size_y):
                block_x = x - lt_x
                block_y = y - lt_y
                if block_x < 0 or block_y < 0:
                    continue
                if block_x >= self.display_size or block_y >= self.display_size:
                    continue
                if abs(x - agent_x) + abs(y - agent_y) <= self.current_vision_range:
                    continue
                self.screen.blit(
                    surf_scale(self.assets[FOG_ASSET_NAME[int(self.is_daytime)]], [self.block_size] * 2),
                    ((1 + block_x) * self.block_size, (1 + block_y) * self.block_size)
                )
        cursor += 2
        return cursor

    def _draw_attribute(self, cursor):
        # attribute
        attribute_num = int(self.ui_info[cursor])
        cursor += 1
        shift_x = 1
        shift_y = 2 + self.display_size
        for i in range(attribute_num):
            y = int((shift_y + i / 2) * self.block_size)
            x = int(shift_x * self.block_size)
            self.screen.blit(
                self.font.render(f"{self.env.attribute_name[i]:15s}{int(self.ui_info[cursor]):5d}", True, FONT_WHITE),
                (x, y)
            )
            if self.env.attribute_name[i] == 'Vision' and self.is_daytime:
                self.current_vision_range = int(self.ui_info[cursor])
            elif self.env.attribute_name[i] == 'NightVision' and not self.is_daytime:
                self.current_vision_range = int(self.ui_info[cursor])
            cursor += 1
        self.screen.blit(
            self.font.render("Attribute", True, FONT_WHITE),
            [int((shift_x + .25) * self.block_size), int((shift_y - .75) * self.block_size)]
        )
        return cursor

    def _draw_backpack(self, cursor):
        backpack_size = int(self.ui_info[cursor])
        cursor += 1
        shift_x = 2 + self.display_size
        shift_y = 1
        for i in range(backpack_size):
            y = i // 10
            x = i - y * 10
            x += shift_x
            y += shift_y
            self.screen.blit(
                surf_scale(self.assets['slot_bp'], [self.block_size] * 2),
                (x * self.block_size, y * self.block_size)
            )
            if int(self.ui_info[cursor]) >= 0:
                name = self.env.backend_cfg.typeid2name[f"item:{int(self.ui_info[cursor])}"]
                self.screen.blit(
                    surf_scale(self._get_asset(name), [self.block_size] * 2),
                    (x * self.block_size, y * self.block_size)
                )
                self.screen.blit(
                    self.font.render(str(int(self.ui_info[cursor+1])), True, FONT_WHITE),
                    (int((x + 0.15) * self.block_size), int((y + 0.15) * self.block_size))
                )
            self.nameint[x, y] = int(self.ui_info[cursor])
            cursor += 2
        self.screen.blit(
            self.font.render("Backpack", True, FONT_WHITE),
            [int((shift_x + .25) * self.block_size), int((shift_y - .75) * self.block_size)]
        )
        return cursor

    def _draw_equipment(self, cursor):
        equipment_size = int(self.ui_info[cursor])
        cursor += 1
        shift_x = 2 + self.display_size
        shift_y = 2 + self.backpack_line_n
        for i in range(equipment_size):
            y = i // 10
            x = i - y * 10
            x += shift_x
            y += shift_y
            self.screen.blit(
                surf_scale(self.assets['slot_eq'], [self.block_size] * 2),
                (x * self.block_size, y * self.block_size)
            )
            if int(self.ui_info[cursor]) >= 0:
                name = self.env.backend_cfg.typeid2name[f"item:{int(self.ui_info[cursor])}"]
                self.screen.blit(
                    surf_scale(self._get_asset(name), [self.block_size] * 2),
                    (x * self.block_size, y * self.block_size)
                )
            self.nameint[x, y] = int(self.ui_info[cursor])
            cursor += 1
        self.screen.blit(
            self.font.render("Equipment", True, FONT_WHITE),
            [int((shift_x + .25) * self.block_size), int((shift_y - .75) * self.block_size)]
        )
        return cursor

    def _draw_synthesize_list(self):
        shift_x = 2 + self.display_size
        shift_y = 3 + self.backpack_line_n + self.equipment_line_n
        for i in range(len(self.env.synthesize_list)):
            y = i // 10
            x = i - y * 10
            x += shift_x
            y += shift_y
            name = self.env.backend_cfg.typeid2name[f"item:{self.env.synthesize_list[i]}"]
            self.screen.blit(
                surf_scale(self._get_asset(name), [self.block_size] * 2),
                (x * self.block_size, y * self.block_size)
                )
            self.nameint[x, y] = self.env.synthesize_list[i]
        self.screen.blit(
            self.font.render("Synthesize List", True, FONT_WHITE),
            [int((shift_x + .25) * self.block_size), int((shift_y - .75) * self.block_size)]
        )
    
    def _draw_info(self):
        x = 8
        y = 2 + self.display_size
        self.screen.blit(
            self.font.render(f"Information", True, FONT_WHITE),
            [int((x + .25) * self.block_size), int((y - .75) * self.block_size)]
        )
        shift_pixel_x = 0
        shift_pixel_y = 0
        for word in self.mouse_info.split(' '):
            word_surf = self.font.render(word + ' ', True, FONT_WHITE)
            if x * self.block_size + shift_pixel_x + word_surf.get_width() >= (1 + self.display_size) * self.block_size:
                shift_pixel_y += self.block_size // 2
                shift_pixel_x = 0
            self.screen.blit(word_surf, [x * self.block_size + shift_pixel_x, y * self.block_size + shift_pixel_y])
            shift_pixel_x += word_surf.get_width()

    def _get_display_rect(self):
        cursor = 1 + self.env.map_size_x * self.env.map_size_y * 6 + 1 # weather, map, daytime
        agent_x = self.ui_info[cursor]
        agent_y = self.ui_info[cursor+1]
        left_top_x = max(0, min(self.env.map_size_x - self.display_size, agent_x - self.display_size // 2))
        left_top_y = max(0, min(self.env.map_size_y - self.display_size, agent_y - self.display_size // 2))
        return int(left_top_x), int(left_top_y)
    
    def _get_asset(self, name):
        assert name in self.assets.keys(), "Could not find {name} in assets"
        return self.assets[name]

if __name__ == "__main__":
    import gym, eden
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument('--load_history', '-l', action='store_true', help='whether to load actions from history.log')
    parser.add_argument('--display_size', '-d', type=int, default=20, help='the map display size, should be no less than 16')
    args = parser.parse_args()

    env = gym.make('eden-v0')
    env.reset()
    if args.load_history:
        action_history = []
        with open('history.log', 'r') as file:
            lines = file.readlines()
            for line in lines:
                if '[[' not in line:
                    continue
                multi_action = line[:-1].strip('[]').split('], [')
                action_history.append([[int(x) for x in single_action.split(', ')] for single_action in multi_action])
        for action in action_history:
            env.step(action)
    render = Render(env, display_size=args.display_size)
    render.ui_run()
