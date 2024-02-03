import pygame as pg

from shapely.geometry import Polygon
from shapely.affinity import rotate


# Colors from here: https://github.com/dracula/dracula-theme
BLACK       = pg.Color('#121212')
CYAN        = pg.Color('#8be9fd')
DARK        = pg.Color('#282a36')
GRAY        = pg.Color('#44475a')
GREEN       = pg.Color('#50fa7b')
RED         = pg.Color('#ff5555')
TRANSPARENT = pg.Color('#ff00ff')
YELLOW      = pg.Color('#f5b631')


def increment_with_rollover(value: int, delta: int, rollover: int) -> int:
    value += delta

    if value < rollover:
        return value

    return value - rollover

def rotate_image(image: pg.Surface, angle: int, destination: tuple[int]) -> tuple[pg.Surface, pg.Rect]:
    destination = pg.Vector2(destination)

    rotated = pg.transform.rotate(image, angle * -1)
    rect = rotated.get_rect(center=(rotated.get_width() // 2, rotated.get_height() // 2))
    destination_delta = pg.Vector2(destination.x - rect.center[0], destination.y - rect.center[1])
    rect.x += destination_delta.x
    rect.y += destination_delta.y
    return rotated, rect


def main():
    pg.init()
    pg.display.set_caption('FFX Battle Intro')
    screen = pg.display.set_mode((150, 150), pg.SCALED)
    clock = pg.time.Clock()

    original_image = pg.image.load('calm_lands.png')
    image_poly_points = [(85, 209), (177, 226), (67, 229)]
    poly = Polygon(image_poly_points)
    x_min, y_min, x_max, y_max = poly.bounds
    poly_width = x_max - x_min
    poly_height = y_max - y_min
    cropped_image = original_image.subsurface(pg.Rect(x_min, y_min, poly_width, poly_height))
    screen_poly_points = [pg.Vector2(p) - (67, 209) for p in poly.exterior.coords]
    screen_poly_points = [pg.Vector2(p) + (75, 75) - (poly_width // 2, poly_height // 2) for p in screen_poly_points]
    poly = Polygon(screen_poly_points)

    rotation_angle = 0
    rotation_delta = 2
    display_surface = pg.Surface((150, 150))
    running = True

    while running:
        clock.tick(30)

        for event in pg.event.get():
            if event.type == pg.QUIT:
                running = False

        rotation_angle = increment_with_rollover(rotation_angle, rotation_delta, 360)
        rotated_image, rotated_rect = rotate_image(cropped_image, angle=rotation_angle, destination=(75, 75))

        poly = rotate(poly, rotation_delta, origin=(75, 75))

        display_surface.fill(pg.Color('#000000'))
        pg.draw.polygon(display_surface, pg.Color('#ffffff'), poly.exterior.coords)
        display_surface.blit(rotated_image, rotated_rect, special_flags=pg.BLEND_RGBA_MIN)


        screen.fill(BLACK)
        screen.blit(display_surface, (0, 0))

        pg.draw.polygon(screen, RED, poly.exterior.coords, 2)

        pg.display.flip()


if __name__ == '__main__':
    main()
