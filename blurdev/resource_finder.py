from __future__ import absolute_import
import os

from pathlib2 import Path

from pillar.resource_finder import ResourceFinder as PillarResourceFinder


class ResourceFinder(PillarResourceFinder):

    """Subclass that adds child finders for the production library and blurdevs own
    resource folder.
    """

    def __init__(self):
        # Set the resource cache for local resource caching.
        cache_root = os.getenv('BDEV_RESOURCES_CACHE')
        use_caching = os.getenv('BDEV_CACHE_RESOURCES', 'true')
        allow_caching = use_caching.lower() in ('true', 'yes')
        if cache_root and allow_caching:
            cache_path = Path(cache_root)
            cache_path = cache_path / 'blurdev'
            cache = str(cache_path)
        else:
            cache = None

        super(ResourceFinder, self).__init__('blurdev', '', cache_paths=cache)

        # Build blurdev resource finder.
        path = Path(__file__).parents[0] / 'resource'
        PillarResourceFinder(
            'resources', str(path), cache_paths="resources", parent=self
        )

        # Build library finder.
        PillarResourceFinder(
            'library',
            os.getenv('BDEV_PATH_RESOURCES', ''),
            cache_paths="library",
            parent=self,
        )
