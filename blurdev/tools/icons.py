from blurdev.gui import IconFactory


def _buildIconFactory():
    from pathlib2 import Path

    local_path = Path(__file__).parents[0]
    presets_file = str(local_path / 'icon_presets.yaml')

    # Setup icon factory.
    factory = IconFactory().customize(
        iconClass='StyledIcon', finders=['library-icons.google'], presets=presets_file
    )

    return factory


iconFactory = _buildIconFactory()
del _buildIconFactory
