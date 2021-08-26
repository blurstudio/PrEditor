from __future__ import absolute_import
from pillar.resource_finder import ResourceFinder as PillarResourceFinder


class ResourceFinder(PillarResourceFinder):

    """ Subclass that adds child finders for the production library and blurdevs own
        resource folder.
    """

    def __init__(self):
        super(ResourceFinder, self).__init__('blurdev', '')

        # Build child finder.
        import os

        from pathlib2 import Path

        # Build blurdev resource finder.
        path = Path(__file__).parents[0] / 'resource'
        PillarResourceFinder('resources', str(path), parent=self)

        # Build library finder.
        PillarResourceFinder('library', os.environ['BDEV_PATH_RESOURCES'], parent=self)
