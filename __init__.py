def classFactory(iface):
    from .urbismap_plugin import UrbisMapPlugin
    return UrbisMapPlugin(iface)
