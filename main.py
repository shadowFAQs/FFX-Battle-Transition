import math
import random

import numpy as np
import pygame as pg
import pytweening

from scipy.spatial import Voronoi
from shapely.geometry import Polygon
from shapely.affinity import rotate, scale, translate


# Colors from https://github.com/dracula/dracula-theme
DARKEST     = pg.Color('#121212')
CYAN        = pg.Color('#8be9fd')
DARK        = pg.Color('#282a36')
GRAY        = pg.Color('#44475a')
GREEN       = pg.Color('#50fa7b')
RED         = pg.Color('#ff5555')
TRANSPARENT = pg.Color('#ff00ff')
YELLOW      = pg.Color('#f5b631')


class Shard():
    def __init__(self, image: pg.Surface, poly: Polygon, offset: tuple[int]):
        self.poly = poly
        self.offset = offset

        x_min, y_min, x_max, y_max = self.poly.bounds
        poly_width = x_max - x_min
        poly_height = y_max - y_min

        self.cropped_rect = pg.Rect(x_min - self.offset[0], y_min - self.offset[1], poly_width, poly_height)
        self.cropped_image = image.subsurface(self.cropped_rect)
        self.friction = 0.92
        self.in_motion = False
        self.masked_poly = None  # pg.Surface
        self.motion_frame = 0
        self.rotated_rect = self.cropped_rect.copy()
        self.rotation_angle = 0
        self.topleft = (x_min - self.offset[0], y_min - self.offset[1])
        self.tween_coords = []

        self.create_masked_poly()
        self.set_rotation(-1, 1)  # Create a little initial motion in the pattern of cracks

    def begin_sweep(self):
        self.in_motion = True
        self.friction = 1
        self.rotation_delta = random.choice([-5, -4, -3, 3, 4, 5])

    def centroid_tuple(self) -> tuple[float]:
        return self.poly.centroid.x, self.poly.centroid.y

    def create_masked_poly(self):
        poly_points = [tuple([p[0] - self.topleft[0] - self.offset[0],
                             p[1] - self.topleft[1] - self.offset[1]]) for p in self.poly.exterior.coords]

        surface = self.cropped_image.copy()
        surface.fill(pg.Color('#000000'))
        pg.draw.polygon(surface, pg.Color('#ffffff'), poly_points)
        surface.blit(self.cropped_image, (0, 0), special_flags=pg.BLEND_RGBA_MIN)

        pxarray = pg.PixelArray(surface)
        pxarray.replace(pg.Color('#000000'), TRANSPARENT)

        self.masked_poly = surface
        self.masked_poly = pxarray.make_surface()
        self.masked_poly.set_colorkey(TRANSPARENT)

    def rotate_image(self, destination: tuple[int]) -> tuple[pg.Surface, pg.Rect]:
        destination = pg.Vector2(destination)

        rotated = pg.transform.rotate(self.masked_poly, self.rotation_angle * -1)
        rect = rotated.get_rect(center=(rotated.get_width() // 2, rotated.get_height() // 2))
        destination_delta = pg.Vector2(destination.x - rect.center[0], destination.y - rect.center[1])
        self.rotated_rect.x += destination_delta.x
        self.rotated_rect.y += destination_delta.y

        self.rotated_image = rotated
        self.rotated_rect = rect

    def set_rotation(self, range_min: int, range_max: int):
        self.rotation_delta = random.uniform(range_min, range_max)

    def set_topleft(self):
        x_min, y_min, x_max, y_max = self.poly.bounds
        self.topleft = (x_min, y_min)

    def translate(self):
        if not self.tween_coords:
            start_x = self.topleft[0]
            end_x = -start_x - 200
            self.tween_coords = [start_x + pytweening.easeInOutQuint(f / 60) * end_x for f in range(60)]

        delta = self.tween_coords[self.motion_frame] - self.topleft[0]
        self.poly = translate(self.poly, delta)

    def update(self):
        self.rotation_angle += self.rotation_delta
        self.rotation_delta = self.rotation_delta * self.friction if abs(self.rotation_delta) > .05 else 0

        self.rotate_image(destination=self.centroid_tuple())
        self.poly = rotate(self.poly, self.rotation_delta, origin=self.poly.centroid)

        if self.in_motion:
            self.translate()
            self.motion_frame = min(self.motion_frame + 1, len(self.tween_coords) - 1)

        self.set_topleft()


def create_shards(bounding_box_offset: pg.Vector2, bounding_box_size: pg.Vector2, image: pg.Surface) -> list[Shard]:
    vertices = create_vertices(bounding_box_offset, bounding_box_size)
    return create_voronoi_shards(vertices, bounding_box_offset, bounding_box_size, image)


def create_vertices(bounding_box_offset: pg.Vector2, bounding_box_size: pg.Vector2,
                    num_vertices:int = 100) -> list[pg.Vector2]:
    bounding_box_offset = pg.Vector2(bounding_box_offset)
    bounding_box_size = pg.Vector2(bounding_box_size)

    random_vertices = [pg.Vector2(p) for p in list(zip(
        np.random.uniform(bounding_box_offset.x, bounding_box_offset.x + bounding_box_size.x, num_vertices),
        np.random.uniform(bounding_box_offset.y, bounding_box_offset.y + bounding_box_size.y, num_vertices)))]

    # For each vert, reflect it across the vertical and horizontal axes it's closest to.
    # Adding these reflected verts to our initial set ensures the diagram includes the edges of our bounding box.
    reflected = []
    for pt in random_vertices:
        boundary_line_right = bounding_box_offset.x + bounding_box_size.x
        delta = boundary_line_right - pt.x
        if delta < bounding_box_offset.x:
            reflected.append(pg.Vector2(boundary_line_right + delta, pt.y))

        boundary_line_left = bounding_box_offset.x
        delta = boundary_line_left - pt.x
        if delta < bounding_box_offset.x:
            reflected.append(pg.Vector2(boundary_line_left + delta, pt.y))

        boundary_line_top = bounding_box_offset.y
        delta = pt.y - boundary_line_top
        if delta < bounding_box_offset.y:
            reflected.append(pg.Vector2(pt.x, boundary_line_top - delta))

        boundary_line_bottom = bounding_box_offset.y + bounding_box_size.y
        delta = boundary_line_bottom - pt.y
        if delta < bounding_box_offset.y:
            reflected.append(pg.Vector2(pt.x, boundary_line_bottom + delta))

    return random_vertices + reflected


def create_voronoi_shards(vertices: list[pg.Vector2], bounding_box_offset: pg.Vector2,
                          bounding_box_size: pg.Vector2, image: pg.Surface) -> list[Shard]:
    vor = Voronoi(np.array([[v.x, v.y] for v in vertices]))

    polygons = []
    for region in vor.regions:
        polygons.append(Polygon(vor.vertices[region]))

    # Drop polygons which have any points outside the bounding box
    filtered_polys = []
    for poly in polygons:
        drop = False

        if not len(poly.exterior.coords):
            drop = True

        for pt in poly.exterior.coords:
            if pt[0] < bounding_box_offset.x - 1 or pt[0] > bounding_box_offset.x + bounding_box_size.x + 1:
                drop = True
            if pt[1] < bounding_box_offset.y - 1 or pt[1] > bounding_box_offset.y + bounding_box_size.y + 1:
                drop = True
        if not drop:
            filtered_polys.append(poly)

    polygons = None

    # Scale down each poly & create Shard objects
    shards = []
    for poly in filtered_polys:
        shards.append(Shard(image, scale(poly, 0.9, 0.9), bounding_box_offset))

    return shards


def main():
    """
    Shatter transition
    Reference: https://www.youtube.com/watch?v=HKhcqwBrt1Y

    1. Cracks appear in the image; a white "glare" filter is applied and fades; takes about 0.6 seconds
    2. Pieces tilt slightly at random angles
        a. They may overlap each other slightly at this point
    3. Pieces are swept off-screen to the left or right; motion blur and random rotations are applied
        a. Motion "sweeps" across from near-side to far w.r.t. the direction in which pieces are swept off
    """

    pg.init()
    pg.display.set_caption('FFX Shatter Transition')
    screen_dims = (768, 768)
    bounding_box_offset = pg.Vector2(128, 128)
    bounding_box_size = pg.Vector2(512, 512)
    screen = pg.display.set_mode(screen_dims)
    clock = pg.time.Clock()

    image = pg.image.load('zanarkand.png')
    shards = create_shards(bounding_box_offset, bounding_box_size, image)
    glare_alpha_max = 130
    glare_alpha = glare_alpha_max
    glare_counter = 1.0
    sweep_x = bounding_box_offset[0]
    motion_surface = pg.Surface(screen_dims, pg.SRCALPHA)

    cooldown_timer = 0
    paused = True
    motion_blur = False
    reset_ready = False
    running = True

    while running:
        clock.tick(30)

        for event in pg.event.get():
            if event.type == pg.QUIT:
                running = False
            elif event.type == pg.MOUSEBUTTONDOWN:
                if reset_ready:
                    shards = create_shards(bounding_box_offset, bounding_box_size, image)
                    glare_alpha = glare_alpha_max
                    glare_counter = 1.0
                    sweep_x = bounding_box_offset[0]

                    cooldown_timer = 0
                    paused = True
                    motion_blur = False
                    reset_ready = False
                else:
                    paused = False

        if motion_blur:
            screen.blit(motion_surface, (0, 0))
        else:
            screen.fill(DARKEST)

        if paused:
            screen.blit(image, bounding_box_offset)
        else:
            if glare_alpha:
                glare_surface = pg.Surface(screen_dims, pg.SRCALPHA)

            for shard in shards:
                shard.update()
                screen.blit(shard.rotated_image, shard.topleft)
                if glare_alpha:
                    pg.draw.polygon(glare_surface, pg.Color(255, 255, 255, glare_alpha),
                                    shard.poly.exterior.coords)

            # Glare should fade in 0.6 seconds (18 frames)
            if glare_alpha:
                screen.blit(glare_surface, (0, 0))
                glare_alpha = max(math.floor(pytweening.easeInOutQuad(glare_counter) * glare_alpha_max), 0)
                glare_counter -= 1 / 18
            else:
                if sweep_x < screen_dims[0]:
                    sweep_x += random.randint(8, 12)
                for shard in [s for s in shards if s.centroid_tuple()[0] < sweep_x and not s.in_motion]:
                    shard.begin_sweep()

                if motion_blur:
                    motion_surface.blit(screen, (0, 0))
                    alpha = max(int(-0.3 * sweep_x + 310), 64)
                    motion_surface.fill(pg.Color(18, 18, 18, alpha))

                motion_blur = sweep_x > 330  # Delay before starting blur

        if not reset_ready:
            if cooldown_timer:
                cooldown_timer -= 1
                if not cooldown_timer:
                    reset_ready = True
            elif len([s for s in shards if s.motion_frame == len(s.tween_coords) - 1]) == len(shards):
                cooldown_timer = 30  # 1s delay after animation is complete

        pg.display.flip()


if __name__ == '__main__':
    main()
