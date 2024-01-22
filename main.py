import os

import numpy as np
import pygame as pg

from pygame import gfxdraw
from scipy.spatial import Voronoi
from shapely.geometry import Polygon
from shapely.affinity import rotate, scale

from colorized_voronoi import voronoi_finite_polygons_2d  # Source: gist.github.com/pv/8036995


class Shard():
    def __init__(self, polygon: Polygon):
        self.poly = polygon

        self.image_offset = pg.Vector2(0, 0)
        self.rotation = np.random.rand() - 0.5

    def get_int_coords(self) -> tuple[int]:
        return int(self.image_offset.x), -int(self.image_offset.y)

    def move(self, delta: pg.Vector2):
        self.image_offset += delta

        new_coords = []
        for x, y in self.poly.exterior.coords:
            new_coords.append(pg.Vector2(x, y) + delta)

        self.poly = Polygon(new_coords)

    def rotate(self):
        self.rotation = piecewise_floor(v=self.rotation, operand=0.9, threshold=0.1)
        self.poly = rotate(self.poly, self.rotation, origin=self.poly.centroid)


class Transition():
    def __init__(self):
        self.clock = pg.time.Clock()
        self.current_action = ''
        self.expand_rate = 1
        self.frame_counter = 0
        self.image = None
        self.num_shards = 30
        self.screencap = None
        self.shards = []
        self.state = ''

        self.setup_key_frames()
        self.load_image()

    def begin(self):
        if not self.frame_counter:
            self.frame_counter = 1

    def create_shards(self):
        random_seeds = np.random.rand(self.num_shards, 2) * 512
        vor = Voronoi(random_seeds)
        regions, vertices = voronoi_finite_polygons_2d(vor)

        self.shards = []
        for reg in regions:
            poly = Polygon(vertices[reg])
            # Scale down polygons to create "cracks" between them
            scaled_poly = scale(poly, xfact=0.98, yfact=0.98, origin='centroid')
            # Populate shard objects
            self.shards.append(Shard(scaled_poly))

    def draw(self):
        self.image.fill(pg.Color(0, 0, 0, 255))

        if not self.shards:
            self.image.blit(self.screencap, (0, 0))

        for shard in self.shards:
            # shard.image = pg.transform.rotate(self.image, shard.rotation)
            coords = list(shard.poly.exterior.coords)
            gfxdraw.textured_polygon(self.image, coords, self.screencap, *shard.get_int_coords())
            gfxdraw.polygon(self.image, coords, pg.Color(255, 255, 255))

    def end(self):
        print('end')
        self.frame_counter = 0
        self.state = ''

    def expand(self):
        print('expand')

        screen_center = pg.Vector2(255, 255)
        for shard in self.shards:
            direction_vector = pg.Vector2(shard.poly.centroid.x, shard.poly.centroid.y) - screen_center
            direction_vector.normalize_ip()
            velocity_vector = direction_vector * self.expand_rate
            shard.move(velocity_vector)

            shard.rotate()

        self.slow_expansion()

    def load_image(self):
        self.screencap = pg.image.load('calm_lands.png').convert_alpha()
        self.image = pg.Surface(self.screencap.get_size())
        # self.image.set_colorkey(pg.Color(255, 0, 255))

    def setup_key_frames(self):
        self.key_frames      = ['' for _ in range(180)]
        self.key_frames[1]   = 'shatter'
        self.key_frames[2]   = 'expand'
        self.key_frames[60]  = 'stop_expansion'
        self.key_frames[120] = 'sweep'
        self.key_frames[-1]  = 'end'

    def shatter(self):
        print('shatter')
        self.create_shards()

    def slow_expansion(self):
        self.expand_rate = piecewise_floor(v=self.expand_rate, operand=0.9, threshold=0.1)

    def stop_expansion(self):
        print('stop_expansion')

    def sweep(self):
        print('sweep')

    def update(self):
        if self.frame_counter:
            if self.key_frames[self.frame_counter]:
                self.current_action = self.key_frames[self.frame_counter]

            getattr(self, self.current_action)()

        self.draw()

        if self.frame_counter:
            self.frame_counter += 1


def piecewise_floor(v: int|float, operand: float, threshold: float) -> int|float:
    return 0 if abs(v * operand) < threshold else v * operand


def main():
    """Shatter transition steps:
    1. Cracks appear in the image; a white "glare" filter is applied
        a. Individual pieces are 3D
    2. Cracks expand for several frames and pieces tilt slightly at random angles
        a. Pieces may overlap each other slightly at this point
    3. Pieces are swept off-screen to the left or right; motion blur and random rotations are applied
        a. The motion spreads from near-side to far, w.r.t. the direction in which pieces are swept off

    Reference: https://www.youtube.com/watch?v=HKhcqwBrt1Y
    """

    pg.init()
    pg.display.set_caption('FFX Battle Intro')
    screen = pg.display.set_mode((512, 512))

    transition = Transition()

    running = True

    while running:
        transition.clock.tick(30)

        for event in pg.event.get():
            if event.type == pg.QUIT:
                running = False
            elif event.type == pg.MOUSEBUTTONDOWN:
                if event.button == 1:
                    transition.begin()

        transition.update()

        screen.fill(pg.Color(0, 0, 0))
        screen.blit(transition.image, (0, 0))
        pg.display.flip()


if __name__ == '__main__':
    main()
