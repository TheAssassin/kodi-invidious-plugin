import sys

import invidious_plugin

try:
    from urllib.parse import parse_qs
except ImportError:
    from urlparse import parse_qs

import xbmcplugin


def main():
    base_url = sys.argv[0]
    addon_handle = int(sys.argv[1])
    args = parse_qs(sys.argv[2][1:])

    xbmcplugin.setContent(addon_handle, "videos")

    plugin = invidious_plugin.InvidiousPlugin(base_url, addon_handle, args)
    return plugin.run()


if __name__ == "__main__":
    sys.exit(main())
