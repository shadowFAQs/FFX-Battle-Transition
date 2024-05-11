import math
import random
import sys

import numpy as np
import pygame as pg
import pytweening

from scipy.spatial import Voronoi
from shapely.geometry import Polygon
from shapely.affinity import rotate, scale, translate


DARKEST     = pg.Color('#121212')
TRANSPARENT = pg.Color('#ff00ff')


class Shard():
    def __init__(self, image: pg.Surface, poly: Polygon):
        self.poly = poly

        x_min, y_min, x_max, y_max = self.poly.bounds
        poly_width = x_max - x_min
        poly_height = y_max - y_min

        self.display = True
        self.friction = 0.92
        self.in_motion = False
        self.masked_poly = None  # pg.Surface
        self.motion_frame = 0
        self.rotation_angle = 0
        self.topleft = (x_min, y_min)
        self.tween_coords = []

        self.cropped_rect = pg.Rect(x_min, y_min, poly_width, poly_height)
        self.cropped_image = image.subsurface(self.cropped_rect)
        self.rotated_rect = self.cropped_rect.copy()

        self.create_masked_poly()
        self.set_rotation(-1, 1)  # Create a little initial motion in the pattern of cracks

    def begin_sweep(self):
        self.in_motion = True
        self.friction = 1
        self.rotation_delta = random.choice([-5, -4, -3, 3, 4, 5])

    def centroid_vector(self) -> pg.Vector2:
        return pg.Vector2(self.poly.centroid.x, self.poly.centroid.y)

    def create_masked_poly(self):
        poly_points = [tuple([p[0] - self.topleft[0], p[1] - self.topleft[1]]) for p in self.poly.exterior.coords]

        surface = self.cropped_image.copy()
        surface.fill(pg.Color(0, 0, 0))
        pg.draw.polygon(surface, pg.Color(255, 255, 255), poly_points)
        surface.blit(self.cropped_image, (0, 0), special_flags=pg.BLEND_RGBA_MIN)

        pxarray = pg.PixelArray(surface)
        pxarray.replace(pg.Color(0, 0, 0), TRANSPARENT)

        self.masked_poly = surface
        self.masked_poly = pxarray.make_surface()
        self.masked_poly.set_colorkey(TRANSPARENT)

    def rotate_image(self) -> tuple[pg.Surface, pg.Rect]:
        self.rotated_image = pg.transform.rotate(self.masked_poly, self.rotation_angle * -1)
        self.rect = self.rotated_image.get_rect()
        centroid_delta = self.centroid_vector() - self.rect.center

        self.topleft = tuple(self.rect.topleft + centroid_delta)

    def set_rotation(self, range_min: int, range_max: int):
        self.rotation_delta = random.uniform(range_min, range_max)

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

        self.rotate_image()
        self.poly = rotate(self.poly, self.rotation_delta, origin=self.poly.centroid)

        if self.in_motion:
            self.translate()
            self.motion_frame = min(self.motion_frame + 1, len(self.tween_coords) - 1)

            if self.motion_frame == len(self.tween_coords) - 1:
                self.display = False


def create_shards(screen_dims: tuple[int], image: pg.Surface) -> list[Shard]:
    vertices = create_vertices(screen_dims)
    return create_voronoi_shards(vertices, screen_dims, image)


def create_vertices(screen_dims: tuple[int], num_vertices: int = 100) -> list[pg.Vector2]:
    random_vertices = [pg.Vector2(p) for p in list(zip(
        np.random.uniform(0, screen_dims[0], num_vertices),
        np.random.uniform(0, screen_dims[1], num_vertices)))]

    # For each vert, reflect it across all screen edges.
    # Adding these reflected verts to the initial set ensures the diagram includes lines along the screen edges.
    reflected = []
    for pt in random_vertices:
        delta = screen_dims[0] - pt.x
        reflected.append(pg.Vector2(pt.x * -1, pt.y))               # Reflect across left edge
        reflected.append(pg.Vector2(screen_dims[0] + delta, pt.y))  # Reflect across right edge

        delta = screen_dims[1] - pt.y
        reflected.append(pg.Vector2(pt.x, screen_dims[1] + delta))  # Reflect across bottom edge
        reflected.append(pg.Vector2(pt.x, pt.y * -1))               # Reflect across top edge

    return random_vertices + reflected


def create_voronoi_shards(vertices: list[pg.Vector2], screen_dims: tuple[int], image: pg.Surface) -> list[Shard]:
    vor = Voronoi(np.array([[v.x, v.y] for v in vertices]))

    polygons = []
    for region in vor.regions:
        polygons.append(Polygon(vor.vertices[region]))

    # Drop polygons which have any points outside the bounding box
    filtered_polys = []
    for poly in polygons:
        valid = True

        if len(poly.exterior.coords):
            for pt in poly.exterior.coords:
                if pt[0] < -1 or pt[0] > screen_dims[0] + 1:
                    valid = False
                    break
                if pt[1] < -1 or pt[1] > screen_dims[1] + 1:
                    valid = False
                    break

            if valid:
                filtered_polys.append(poly)

    polygons = None

    # Scale down each poly & create Shard objects
    shards = []
    for poly in filtered_polys:
        shards.append(Shard(image, scale(poly, 0.9, 0.9)))

    return shards


def resize_image_and_set_dims(filename: str, max_size: int) -> tuple:
    image = pg.image.load(filename)
    image_w, image_h = image.get_size()

    if max(image_w, image_h) > max_size:
        if image_w > image_h:  # Landscape
            image = pg.transform.scale(image, (max_size, int(image_h * (max_size / image_w))))
        else:  # Portrait / square
            image = pg.transform.scale(image, (int(image_w * (max_size / image_h)), max_size))

    return image, image.get_size()


def main(filename: str='zanarkand.png'):
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
    image, screen_dims = resize_image_and_set_dims(filename, max_size=512)
    screen = pg.display.set_mode(screen_dims)
    clock = pg.time.Clock()
    target_framerate = 30

    shards = create_shards(screen_dims, image)
    glare_alpha_max = 130
    glare_alpha = glare_alpha_max
    glare_counter = 1.0
    sweep_x = 16
    motion_surface = pg.Surface(screen_dims, pg.SRCALPHA)

    cooldown_timer = 0
    paused = True
    motion_blur = False
    reset_ready = False
    running = True

    while running:
        clock.tick(target_framerate)

        for event in pg.event.get():
            if event.type == pg.QUIT:
                running = False
            elif event.type == pg.MOUSEBUTTONDOWN:
                if reset_ready:
                    shards = create_shards(screen_dims, image)
                    glare_alpha = glare_alpha_max
                    glare_counter = 1.0
                    sweep_x = 16

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
            screen.blit(image, (0, 0))
        else:
            if glare_alpha:
                glare_surface = pg.Surface(screen_dims, pg.SRCALPHA)

            for shard in shards:
                shard.update()

                if shard.display:
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
                for shard in [s for s in shards if s.centroid_vector().x < sweep_x and not s.in_motion]:
                    shard.begin_sweep()

                if motion_blur:
                    motion_surface.blit(screen, (0, 0))
                    alpha = max(int(-0.15 * sweep_x + 170), 50)
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
    try:
        main(sys.argv[1])
    except IndexError:
        main()
