# FFX style "shatter/sweep" transition

![](demo_zanarkand.gif)

Uses [pygame](https://github.com/pygame/pygame), [numpy](https://numpy.org/), [pytweening](https://github.com/asweigart/pytweening), [scipy](https://scipy.org/) and [shapely](https://pypi.org/project/shapely/)

### Try it out:
* Specify an image filename: `python main.py midboss.png`
* Click anywhere on the pygame window

### A note:
The real FFX shattered glass pattern [is the same every time](https://www.youtube.com/watch?v=HKhcqwBrt1Y), but this one is created on the fly with Voronoi diagrams.
