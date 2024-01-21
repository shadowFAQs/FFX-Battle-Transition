import os

import numpy as np
import pygame as pg
from pygame import gfxdraw
from scipy.spatial import ConvexHull, Voronoi


class Transition():
    def __init__(self):
        self.clock = pg.time.Clock()
        self.frame_counter = 0
        self.image = None
        self.num_vertices = 20
        self.screencap = None
        self.polygons = []
        self.state = ''

        self.setup_key_frames()
        self.load_image()

    def begin(self):
        if not self.frame_counter:
            self.frame_counter = 1

    def create_vertices(self):
        # Generate random 2D points
        points = np.random.rand(self.num_vertices, 2) * 512
        edge_points = np.array([[0, 0], [0, 512], [512, 0], [512, 512]])
        points = np.append(points, edge_points, axis=0)

        # Compute Voronoi tesselation
        vor = Voronoi(points)

        # Calculate the convex hull of the points
        hull = ConvexHull(points)
        for vertex in hull.vertices:
            points = np.append(points, [points[vertex]], axis=0)

        # Recalculate the Voronoi diagram
        vor = Voronoi(points)

        # Print the coordinates of each vertex
        for i, region in enumerate(vor.regions):
            if len(region) > 0:
                polygon = []
                for ind in region:
                    polygon.append(vor.vertices[ind])
                self.polygons.append(polygon)

    def draw(self):
        self.image.fill(pg.Color(0, 0, 0))

        if not self.polygons:
            self.image.blit(self.screencap, (0, 0))

        for polygon in self.polygons:
            gfxdraw.filled_polygon(self.image, polygon, pg.Color(255, 0, 0))
            gfxdraw.polygon(self.image, polygon, pg.Color(255, 255, 255))

    def end(self):
        print('end')
        self.frame_counter = 0
        self.state = ''

    def load_image(self):
        self.screencap = pg.image.load('calm_lands.png')
        self.image = pg.Surface(self.screencap.get_size())

    def setup_key_frames(self):
        self.key_frames = ['' for _ in range(100)]
        self.key_frames[1]  = 'shatter'
        self.key_frames[20] = 'stop_expansion'
        self.key_frames[40] = 'sweep'
        self.key_frames[-1] = 'end'

    def shatter(self):
        print('shatter')
        self.create_vertices()

    def stop_expansion(self):
        print('stop_expansion')

    def sweep(self):
        print('sweep')

    def update(self):
        if self.frame_counter:
            if self.key_frames[self.frame_counter]:
                getattr(self, self.key_frames[self.frame_counter])()

        self.draw()

        if self.frame_counter:
            self.frame_counter += 1


def main():
    """Shatter transition steps:
    1. Cracks appear in the image; a white "glare" filter is applied
        a. Individual pieces are 3D
    2. Cracks expand for several frames and pieces tilt slightly at random
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
