# quick code to get multiply and bake working from within the editor

from PIL.ImageGrab import grabclipboard as cb_img
from random import randrange
from enum import Enum, auto

from os import environ
from os.path import dirname
environ['PYGAME_HIDE_SUPPORT_PROMPT'] = 'hide'

import pygame
from pygame.locals import *
pygame.font.init()
font  = pygame.font.Font(f'{dirname(__file__)}/Product Sans Regular.ttf', 20)
sfont = pygame.font.Font(f'{dirname(__file__)}/Product Sans Regular.ttf', 16)

from tkinter.filedialog import asksaveasfilename as tksave
from tkinter.filedialog import askopenfilename as tkopen
from tkinter import Tk

root = Tk()
root.withdraw()

from editor_objects import Buffer, Layer, Layer_group, PointBuffer
import editor_objects as assets

c = type('c', (), {'__matmul__': (lambda s, x: (*x.to_bytes(3, 'big'),)), '__sub__': (lambda s, x: (x&255,)*3)})()
green = c@0xa0ffe0
grey = (*c-50, 80)

bg = c-27
fg = c@0xff9088
hover_colour = (*c-100, 80)
sel_fg = green
sel2_fg = c@0xe0a0ff

view_mode_colour   = c@0x40a000
add_mode_colour    = c@0xa02000
source_mode_colour = c@0x0040a0
group_mode_colour  = c@0x8000a0
effect_mode_colour = c-50
point_mode_colour  = c@0x402030

fps = 60

w, h = res = (1500, 900)

def updateStat(msg = None, update = True):
	rect = (0, h-30, w, 31)
	if   curr_mode is Modes.View_select:
		col = view_mode_colour
	elif curr_mode is Modes.Add_layer:
		col = add_mode_colour
	elif curr_mode is Modes.Source_select:
		col = source_mode_colour
	elif curr_mode is Modes.Point:
		col = point_mode_colour
	elif curr_mode is Modes.Group_select:
		col = group_mode_colour
	elif curr_mode is Modes.Effect_select:
		col = effect_mode_colour
	else:
		col = c-0

	display.fill(col, rect)

	tsurf = sfont.render(msg or
		f'[{curr_mode.name.replace("_", " ").upper()}] {curr_layer_group.name}',
		True, c--1)
	display.blit(tsurf, (5, h-25))

	if update: pygame.display.update(rect)

def resize(size):
	global w, h, res, display
	w, h = res = size
	display = pygame.display.set_mode(res, RESIZABLE)
	updateDisplay()

def updateDisplay():
	display.fill(bg)

	# get index from mouse pos
	mouse_pos = pygame.mouse.get_pos()
	index = Panel.get_index(mouse_pos)

	view_surf = view_layer_group.render()
	x, y = ((w-view_surf.get_width())//2, (h-view_surf.get_height())//2)
	display.blit(view_surf, (x, y))

	lw = left_panel.get_width()
	ew = effects_panel.get_width()
	rw = layers_panel.get_width()

	lsurf = left_panel.render(
		None if mouse_pos[0] > lw else index,
		view_layer_group_index, curr_layer_group_index)
	esurf = effects_panel.render(index if mouse_pos[0] > w-ew-rw else None)
	rsurf = layers_panel.render(index if mouse_pos[0] > w-ew-rw else None,
		selected_layer_index)

	display.blit(lsurf, (0, 0))
	display.blit(esurf, (w-ew, 0))
	display.blit(rsurf, (w-ew-rw, 0))

	updateStat(update = False)
	pygame.display.flip()

def toggleFullscreen():
	global pres, res, w, h, display
	res, pres =  pres, res
	w, h = res
	if display.get_flags()&FULLSCREEN: resize(res)
	else: display = pygame.display.set_mode(res, FULLSCREEN); updateDisplay()

class Panel:
	item_height = 40

	@classmethod
	def get_index(cls, mouse_pos):
		return mouse_pos[1]//cls.item_height

	def __init__(self, font, text_colour, hover_bg, bg, sel_fg):
		self.font = font
		self.text_colour = text_colour
		self.hover_bg = hover_bg
		self.bg = bg
		self.sel_fg = sel_fg
		self.sel2_fg = sel2_fg
		self.items = []

	@staticmethod
	def get_width():
		return 200

	def render(self, index, sel_index=None, sel2_index=None):
		out = pygame.Surface((self.get_width(), h), SRCALPHA)
		out.fill(self.bg)

		if index is not None and index < len(self.items):
			out.fill(self.hover_bg,
				(0, index*self.item_height, self.get_width(), self.item_height))

		for i, item in enumerate(self.items):
			if i == sel_index:
				tsurf = self.font.render(item, True, self.sel_fg)
			elif i == sel2_index:
				tsurf = self.font.render(item, True, self.sel2_fg)
			else:
				tsurf = self.font.render(item, True, self.text_colour)
			out.blit(tsurf, (5, i*self.item_height+7))

		return out

class Modes(Enum):
	View_select   = auto()
	Point         = auto()
	Add_layer     = auto()
	Group_select  = auto()
	Effect_select = auto()
	Source_select = auto()
curr_mode = Modes.View_select

def update_right_panel(layer_group):
	global layers_panel, effects_panel  # just being explicit

	layers_panel.items = [
		layer.get_name()
		for layer in layer_group
	]
	effects_panel.items = [
		layer.effect.__qualname__.removeprefix('effect_')
		for layer in layer_group
	]

def update_left_panel():
	global left_panel  # just being explicit

	# TODO store the buffer objects instead of their names
	left_panel.items = [group.name for group in layer_groups]

def get_point_effect_choice(key):
	if key == K_t: return assets.effect_translate
	if key == K_s: return assets.effect_scale

def get_image_effect_choice(key):
	# Arithmetic
	if key == K_a: return assets.effect_add
	if key == K_d: return assets.effect_diff
	if key == K_m: return assets.effect_multiply
	if key == K_c: return assets.effect_screen

	# Other Binary Effects
	if key == K_r: return assets.effect_resize

	# Unary Effects
	if key == K_s: return assets.effect_source
	if key == K_v: return assets.effect_value
	if key == K_l: return assets.effect_luma

left_panel = Panel(font, fg, hover_colour, grey, green)
layers_panel = Panel(font, fg, hover_colour, grey, green)
effects_panel = Panel(font, fg, hover_colour, grey, green)

# This might have to go
buffers = [
	Buffer('Buffer 1', pygame.Surface((400, 200))),
	Buffer('Just a View', pygame.Surface((600, 200))),
	Buffer('Biffer', pygame.Surface((200, 200))),
]

layer_groups = [
	Layer_group(buffer.name, [Layer(buffer, assets.effect_source)])
	for buffer in buffers
]

curr_layer_group_index = 0
curr_layer_group = layer_groups[curr_layer_group_index]
view_layer_group_index = curr_layer_group_index
view_layer_group = curr_layer_group

selected_layer_index = 0

update_left_panel()

# This one needs types and such
# Maybe layers panel + effects panel as SOA
update_right_panel(curr_layer_group)


pos = [0, 0]
dragging = False

resize(res)
pres = pygame.display.list_modes()[0]
clock = pygame.time.Clock()
running = True
while running:
	for event in pygame.event.get():
		if event.type == KEYDOWN:
			if   event.key == K_F11: toggleFullscreen()

			elif event.mod & (KMOD_LCTRL|KMOD_RCTRL):
				if   event.key == K_v:  # Paste
					img = cb_img()
					if img is None: continue
					mode = img.mode
					size = img.size
					data = img.tobytes()
					clipboard_surf = pygame.image.fromstring(data, size, mode)
					new_buffer = Buffer(
						f'Pasted Image #{randrange(1<<24):06x}',
						clipboard_surf)
					default_layer = Layer(new_buffer, assets.effect_source)
					layer_groups.append(
						Layer_group(new_buffer.name, [default_layer]))
					update_left_panel()

				elif event.key == K_e:  # Export
					file_name = tksave()
					if not file_name: continue

					surf = view_layer_group.render()
					pygame.image.save(surf, file_name)

				elif event.key == K_a:  # Import (Add)
					file_name = tkopen()
					if not file_name: continue

					img_surf = pygame.image.load(file_name)
					new_buffer = Buffer(file_name, img_surf)
					default_layer = Layer(new_buffer, assets.effect_source)
					layer_groups.append(
						Layer_group(new_buffer.name, [default_layer]))
					update_left_panel()

				elif event.key == K_r:  # Reset all caches
					for layer_group in layer_groups:
						layer_group.reset_cache()

			elif curr_mode == Modes.Effect_select:

				curr_mode = Modes.View_select
				if selected_layer_index is None: continue
				selected_layer = curr_layer_group[selected_layer_index]

				if event.key == K_ESCAPE: continue

				elif isinstance(selected_layer.src, PointBuffer):
					effect = get_point_effect_choice(event.key)
				else:
					effect = get_image_effect_choice(event.key)

				if effect is not None:
					selected_layer.effect = effect
					curr_layer_group.reset_cache()
					view_layer_group.reset_cache()
					update_right_panel(curr_layer_group)

			elif curr_mode == Modes.Point:

				curr_mode = Modes.View_select
				if event.key == K_ESCAPE: continue

				if selected_layer_index is None: continue

				selected_layer = curr_layer_group[selected_layer_index]
				if isinstance(selected_layer.src, PointBuffer):
					if event.key == K_h:
						selected_layer.src.x = -selected_layer.src.x
						print('HORIZONTAL FLIP', selected_layer.src.get_xy())
						curr_layer_group.reset_cache()
						view_layer_group.reset_cache()
						update_right_panel(curr_layer_group)
						continue
					if event.key == K_v:
						print('VERTICAL FLIP', selected_layer.src.get_xy())
						selected_layer.src.y = -selected_layer.src.y
						curr_layer_group.reset_cache()
						view_layer_group.reset_cache()
						update_right_panel(curr_layer_group)
						continue

				effect = get_point_effect_choice(event.key)
				if effect is None: continue

				new_layer = Layer(PointBuffer(0, 0), effect)
				curr_layer_group.layers.insert(
					selected_layer_index, new_layer)

				curr_layer_group.reset_cache()
				view_layer_group.reset_cache()
				update_right_panel(curr_layer_group)


			elif event.key == K_ESCAPE:
				if not dragging: running = False
				else:
					dragging = False
					layer = curr_layer_group[selected_layer_index]
					layer.src.set_xy(*initial_value)
					curr_layer_group.reset_cache()
					view_layer_group.reset_cache()
					update_right_panel(curr_layer_group)

			elif event.key == K_v:
				curr_mode = Modes.View_select
			elif event.key == K_a:
				curr_mode = Modes.Add_layer
			elif event.key == K_g:
				curr_mode = Modes.Group_select
			elif event.key == K_s:
				curr_mode = Modes.Source_select
			elif event.key == K_e:
				curr_mode = Modes.Effect_select
			elif event.key == K_p:
				curr_mode = Modes.Point

			# These do not change the current mode
			elif event.key == K_x:  # Delete the Selected Layer
				if event.mod & (KMOD_LSHIFT|KMOD_RSHIFT):  # Delete the Group
					if len(layer_groups) <= 1: continue

					layer_groups.pop(curr_layer_group_index)
					if curr_layer_group_index >= len(layer_groups):
						curr_layer_group_index -= 1
					selected_layer_index = 0

					curr_layer_group = layer_groups[curr_layer_group_index]
					curr_layer_group.reset_cache()
					view_layer_group.reset_cache()
					update_right_panel(curr_layer_group)
					update_left_panel()

				elif selected_layer_index is None: continue
				elif len(curr_layer_group.layers) <= 1: continue
				else:
					curr_layer_group.layers.pop(selected_layer_index)
					if selected_layer_index >= len(curr_layer_group.layers):
						selected_layer_index = 0

					curr_layer_group.reset_cache()
					view_layer_group.reset_cache()
					update_right_panel(curr_layer_group)

			elif event.key == K_d:  # Duplicate
				# print('DUPLICATED')
				if event.mod & (KMOD_LSHIFT|KMOD_RSHIFT):
					curr_layer_group = curr_layer_group.copy()
					curr_layer_group_index = len(layer_groups)
					layer_groups.append(curr_layer_group)
					update_left_panel()
				elif selected_layer_index is None: continue
				else:
					selected_layer = curr_layer_group[selected_layer_index]
					curr_layer_group.layers.insert(
						selected_layer_index, selected_layer.copy())

					curr_layer_group.reset_cache()
					view_layer_group.reset_cache()
					update_right_panel(curr_layer_group)

			elif event.key == K_b:  # Bake the current Layer group into a new buffer
				baked_buffer = Buffer(
					f'Baked {curr_layer_group.name}',
					curr_layer_group.render().copy())
				default_layer = Layer(baked_buffer, assets.effect_source)
				layer_groups.append(
					Layer_group(baked_buffer.name, [default_layer]))
				update_left_panel()


			elif event.key == K_r:  # Move layer up
				if selected_layer_index is None: continue
				if selected_layer_index <= 0: continue

				if selected_layer_index == len(curr_layer_group.layers)-1:
					if isinstance(curr_layer_group[-2], PointBuffer): continue

				curr_layer = curr_layer_group[selected_layer_index]
				curr_layer_group[selected_layer_index] = curr_layer_group[selected_layer_index-1]
				selected_layer_index -= 1
				curr_layer_group[selected_layer_index] = curr_layer

				curr_layer_group.reset_cache()
				view_layer_group.reset_cache()
				update_right_panel(curr_layer_group)

			elif event.key == K_f:  # Move layer down
				if selected_layer_index is None: continue
				if selected_layer_index >= len(curr_layer_group.layers)-1:
					continue

				curr_layer = curr_layer_group[selected_layer_index]

				if selected_layer_index >= len(curr_layer_group.layers)-2:
					if isinstance(selected_layer, PointBuffer): continue

				curr_layer_group[selected_layer_index] = curr_layer_group[selected_layer_index+1]
				selected_layer_index += 1
				curr_layer_group[selected_layer_index] = curr_layer

				curr_layer_group.reset_cache()
				view_layer_group.reset_cache()
				update_right_panel(curr_layer_group)

		elif event.type == VIDEORESIZE:
			if not display.get_flags()&FULLSCREEN: resize(event.size)
		elif event.type == QUIT: running = False
		elif event.type == MOUSEBUTTONDOWN:
			if event.button in (4, 5):
				delta = event.button*2-9
			elif event.button == 1:
				panel_item_index = Panel.get_index(event.pos)

				# check if mouse on right panel
				if event.pos[0] > w - Panel.get_width()*2:
					if panel_item_index >= len(curr_layer_group.layers):
						selected_layer_index = 0
						continue
					selected_layer_index = panel_item_index
					# print('Selected layer', panel_item_index)
					continue

				# check if mouse outside left panel
				if event.pos[0] > Panel.get_width():
					if selected_layer_index is None: continue
					layer = curr_layer_group[selected_layer_index]
					if not isinstance(layer.src, PointBuffer): continue
					initial_position = event.pos
					initial_value = layer.src.get_xy()
					dragging = True
					print('DRAGGING TRUE')
					continue

				if panel_item_index >= len(layer_groups): continue

				if   curr_mode is Modes.View_select:
					view_layer_group_index = panel_item_index
					curr_layer_group_index = panel_item_index
					view_layer_group = layer_groups[panel_item_index]
					curr_layer_group = view_layer_group

					selected_layer_index = 0

					view_layer_group.reset_cache()
					update_right_panel(view_layer_group)

				elif curr_mode is Modes.Group_select:
					curr_layer_group_index = panel_item_index
					selected_layer_index = 0
					curr_layer_group = layer_groups[panel_item_index]

					# curr_layer_group.reset_cache()
					# view_layer_group.reset_cache()
					update_right_panel(curr_layer_group)

				elif curr_mode is Modes.Source_select:
					if selected_layer_index is None: continue

					# There can be a cycle. What does the graph look like?
					# Detect only self cycle for now
					if panel_item_index == curr_layer_group_index: continue

					selected_layer = curr_layer_group[selected_layer_index]
					if isinstance(selected_layer.src, PointBuffer):
						selected_layer.src.set_xy(
							*layer_groups[panel_item_index].render().get_size()
						)
						print('Set xy to', selected_layer.src.get_xy())
					else:
						selected_layer.src = layer_groups[panel_item_index]

					curr_layer_group.reset_cache()
					view_layer_group.reset_cache()
					update_right_panel(curr_layer_group)

				elif curr_mode is Modes.Add_layer:
					if selected_layer_index is None: continue

					# There can be a cycle. What does the graph look like?
					# Detect only self cycle for now
					if panel_item_index == curr_layer_group_index: continue

					new_layer = Layer(
						layer_groups[panel_item_index], assets.effect_source)
					curr_layer_group.layers.insert(
						selected_layer_index, new_layer)

					curr_layer_group.reset_cache()
					view_layer_group.reset_cache()
					update_right_panel(curr_layer_group)

				# dragging = True
			elif event.button == 3:
				print('MOUSE BUTTON 3')
				buffers[0].change_arr()
				curr_layer_group.reset_cache()
				view_layer_group.reset_cache()
		elif event.type == MOUSEBUTTONUP:
			if event.button == 1:
				dragging = False
		elif event.type == MOUSEMOTION:
			# Assuming dragging happens only when a point object is curr_layer
			if dragging:
				# The layer shouldn't change while dragging
				layer = curr_layer_group[selected_layer_index]
				point = layer.src
				x, y = event.pos

				if pygame.key.get_mods() & (KMOD_LSHIFT|KMOD_RSHIFT):
					point.x = initial_value[0] + (x - initial_position[0])//10
					point.y = initial_value[1] + (y - initial_position[1])//10
				else:
					point.x = initial_value[0] + (x - initial_position[0])
					point.y = initial_value[1] + (y - initial_position[1])

				curr_layer_group.reset_cache()
				view_layer_group.reset_cache()
				update_right_panel(curr_layer_group)

	updateDisplay()
	updateStat()
	clock.tick(fps)
