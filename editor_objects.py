# contains classes for layer and buffer objects

import pygame
import numpy as np
from cv2 import resize as arr_resize
from cv2 import INTER_CUBIC as RESIZE_INTERPOLATION

# IMAGE EFFECTS

# source is not unary because unaries use only base. source uses only layer
def effect_source(base, layer):  # applies 'layer' on top of 'base'
	return layer

def effect_multiply(base, layer):
	base = effect_pad(base, layer)
	layer = effect_pad(layer, base)

	return np.array(base*layer // 255, dtype=np.uint8)

def effect_screen(base, layer):
	base = effect_pad(base, layer)
	layer = effect_pad(layer, base)

	return 255 - np.array((255 - base)*(255 - layer) // 255, dtype=np.uint8)

def effect_add(base, layer):
	base = effect_pad(base, layer)
	layer = effect_pad(layer, base)
	return np.array(np.clip(base+layer, 0, 255), dtype=np.uint8)

def effect_diff(base, layer):
	base = effect_pad(base, layer)
	layer = effect_pad(layer, base)
	return np.absolute(np.clip(base-layer, -255, 255))

def effect_resize(base, layer):
	pad_mapping = [*zip(base.shape, layer.shape)]
	print('resize', pad_mapping)
	out_arr = np.zeros(layer.shape, dtype=layer.dtype)
	out_arr[:base.shape[0], :base.shape[1]] = base[:layer.shape[0], :layer.shape[1]]
	print(out_arr.shape)
	print(f'{type(out_arr)}')
	return out_arr

def effect_pad(base, layer):
	'''Takes numpy arrays of same dimensions, or crashes
	TODO: Add guardrails, allow incompatible dimensions'''

	print(base.shape, layer.shape)
	pad_mapping = [*zip(base.shape, layer.shape)]
	print('resize', pad_mapping)
	out_arr = np.zeros([max(i) for i in zip(layer.shape, base.shape)], dtype=np.uint32)
	out_arr[:base.shape[0], :base.shape[1]] = base[:out_arr.shape[0], :out_arr.shape[1]]
	print(out_arr.shape)
	print(f'{type(out_arr)}')
	return out_arr

# UNARY EFFECTS

def effect_value(base, _):
	out_arr = base.sum(axis=2, dtype=np.uint32)//3
	out_arr = np.pad(
		out_arr[:, :, np.newaxis],
		((0, 0), (0, 0), (0, 2)), mode='edge')
	return out_arr

def effect_luma(base, _):
	out_arr = (base*[0.11, 0.59, 0.3]).sum(axis=2)
	out_arr = np.pad(
		out_arr[:, :, np.newaxis],
		((0, 0), (0, 0), (0, 2)), mode='edge')
	return out_arr

# POINT EFFECTS

def effect_translate(base, point):
	out_array = np.zeros(base.shape)

	out_array[
		max(0, point[0]):max(0, point[0]+base.shape[0]),
		max(0, point[1]):max(0, point[1]+base.shape[1]),
	] = base[
		max(0, -point[0]):max(0, -point[0]+base.shape[0]),
		max(0, -point[1]):max(0, -point[1]+base.shape[1]),
	]

	return out_array

def effect_scale(base, point):
	if point[0] == 0 or point[1] == 0: return np.zeros((1, 1, 3))
	if point[0] < 0: base = base[::-1, :]; point[0] = -point[0]
	if point[1] < 0: base = base[:, ::-1]; point[1] = -point[1]
	return arr_resize(base, dsize=point[::-1], interpolation=RESIZE_INTERPOLATION)

# CLASSES

class Layer:
	def __init__(self, src: 'Buffer', effect: callable):
		'''src holds the buffer of the layer
		effect is how it is layered onto another layer'''
		self.src = src
		self.effect = effect

	def render(self, *, base: pygame.Surface = None):
		'''Rendering a layer is expensive. That's why Layer_group caches it.'''
		if base is None: return self.src.render()
		base_arr = pygame.surfarray.pixels3d(base)

		# using duck typing polymorphism
		out_arr = self.effect(base_arr, self.src.get_arr())
		del base_arr
		base.unlock()
		# print('LOCK ON BASE:', base.get_locked())
		# print('output array is of', out_arr.shape)
		return pygame.surfarray.make_surface(out_arr).copy()

	def get_name(self):
		if isinstance(self.src, PointBuffer):
			return f'Point [{self.src.x}, {self.src.y}]'
		else:
			return self.src.name

	def copy(self):
		return self.__class__(self.src, self.effect)

class Layer_group:
	def __init__(self, name, layers):
		self.name = name
		self.layers = layers
		self._cache = None

		if len(self.layers) < 1:
			raise IndexError('Layer groups require at least one layer')

	def __getitem__(self, index):
		return self.layers[index]

	def __setitem__(self, index, value):
		self.layers[index] = value

	def reset_cache(self):
		self._cache = None
	
	def get_arr(self):
		if self._cache is None: self.render()
		return pygame.surfarray.pixels3d(self._cache)

	def render(self):
		if self._cache is not None: return self._cache

		self._cache = self.layers[-1].render()  # get a surface of correct size
		for layer in reversed(self.layers[:-1]):
			self._cache = layer.render(base = self._cache)
		return self._cache

	def copy(self):
		return self.__class__(
			f'Copy of {self.name}', [layer.copy() for layer in self.layers])

# Use it only if you have to.
class Buffer:
	'''
	Stores an array.
	Rendering a buffer produces a surface.
	'''
	def __init__(self, name, surf):
		self.name = name
		self.surf = surf
		# print(self.name+':', 'BUFFER INIT LOCKED:', surf.get_locked())
		self.arr  = pygame.surfarray.pixels3d(surf)
		# print(self.name+':', 'BUFFER INIT LOCKED:', surf.get_locked())

	def get_arr(self):
		return self.arr

	def change_arr(self):  # TEMP
		print(self.name+':', 'CHANGED ARRAY')
		self.arr[...] = ~self.arr[...]
		self.reset_cache()

	def reset_cache(self):
		self.surf = None

	def render(self):
		# TODO: Handle locked surfaces
		if self.surf is None or self.surf.get_size() != self.arr.shape[:2]:
			# print(self.name+':', 'SURF IS NONE')
			self.surf = pygame.surfarray.make_surface(self.arr)
			self.surf.unlock()
			print(self.name+':', 'SURF RESET LOCKED: ', self.surf.get_locked())
		else:
			# print(self.name+':', 'BUFFER RENDER LOCKED:', self.surf.get_locked())
			pygame.surfarray.blit_array(self.surf, self.arr)
			# print(self.name+':', 'BUFFER RENDER LOCKED:', self.surf.get_locked())
		if self.surf.get_locked(): self.surf = self.surf.copy()
		return self.surf

class PointBuffer:
	def __init__(self, x, y):
		self.x = x
		self.y = y

	def set_xy(self, x, y):
		self.x = x
		self.y = y

	def get_xy(self):
		return self.x, self.y

	def get_arr(self):
		return [self.x, self.y]
