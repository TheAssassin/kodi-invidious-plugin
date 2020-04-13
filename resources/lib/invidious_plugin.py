import requests
import sys
from urllib import urlencode
from urlparse import parse_qs

import xbmcgui
import xbmcplugin

import inputstreamhelper

import invidious_api


class InvidiousPlugin:
    def __init__(self, base_url, addon_handle, args):
        self.base_url = base_url
        self.addon_handle = addon_handle
        self.args = args

        instance_url = xbmcplugin.getSetting(self.addon_handle, "instance_url")
        self.api_client = invidious_api.InvidiousAPIClient(instance_url)

    def build_url(self, action, **kwargs):
        if not action:
            raise ValueError("you need to specify an action")

        kwargs["action"] = action

        return self.base_url + "?" + urlencode(kwargs)

    def add_directory_item(self, *args, **kwargs):
        xbmcplugin.addDirectoryItem(self.addon_handle, *args, **kwargs)

    def end_of_directory(self):
        xbmcplugin.endOfDirectory(self.addon_handle)

    def display_search(self):
        # query search terms with a dialog
        dialog = xbmcgui.Dialog()
        search_input = dialog.input("Search", type=xbmcgui.INPUT_ALPHANUM)

        # search for the terms on Invidious
        results = self.api_client.search(search_input)

        # assemble menu with the results
        for video in results:
            list_item = xbmcgui.ListItem(video.title)
            list_item.setArt({
                "thumb": video.thumbnail_url,
            })
            list_item.setInfo("video", {
                "title": video.title,
                "mediatype": "video",
                "plot": video.description,
            })
            # if this is NOT set, the plugin is called with an invalid handle when trying to play this item
            # seriously, Kodi? come on...
            # https://forum.kodi.tv/showthread.php?tid=173986&pid=1519987#pid1519987
            list_item.setProperty("IsPlayable", "true")

            url = self.build_url("play_video", video_id=video.video_id)

            self.add_directory_item(url=url, listitem=list_item)

        self.end_of_directory()

    def play_video(self, id):
        # TODO: add support for adaptive streaming
        video_info = self.api_client.fetch_video_information(id)

        listitem = None

        # check if playback via MPEG-DASH is possible
        if "dashUrl" in video_info:
            is_helper = inputstreamhelper.Helper("mpd")
            
            if is_helper.check_inputstream():
                listitem = xbmcgui.ListItem(path=video_info["dashUrl"])
                listitem.setProperty("inputstreamaddon", is_helper.inputstream_addon)
                listitem.setProperty("inputstream.adaptive.manifest_type", "mpd")

        # as a fallback, we use the first oldschool stream
        if listitem is None:
            url = video_info["formatStreams"][0]["url"]
            # it's pretty complicated to play a video by its URL in Kodi...
            listitem = xbmcgui.ListItem(path=url)

        xbmcplugin.setResolvedUrl(self.addon_handle, succeeded=True, listitem=listitem)

    def display_main_menu(self):
        # video search item
        listitem = xbmcgui.ListItem("Search video titles", path="search_video")
        self.add_directory_item(url=self.build_url("search_video"), listitem=listitem, isFolder=True)

        self.end_of_directory()

    def run(self):
        """
        Web application style method dispatching.
        Uses querystring only, which is pretty oldschool CGI-like stuff.
        """

        action = self.args.get("action", [None])[0]

        # debugging
        print("--------------------------------------------")
        print("base url:", self.base_url)
        print("handle:", self.addon_handle)
        print("args:", self.args)
        print("action:", action)
        print("--------------------------------------------")

        # for the sake of simplicity, we just handle HTTP request errors here centrally
        try:
            if not action:
                self.display_main_menu()

            elif action == "search_video":
                self.display_search()

            elif action == "play_video":
                self.play_video(self.args["video_id"][0])

            else:
                raise RuntimeError("unknown action " + action)

        except requests.HTTPError as e:
            dialog = xbmcgui.Dialog()
            dialog.notification(
                "HTTP error",
                "Request to Invidious API failed: HTTP status " + e.response.status,
                "error"
            )

        except requests.Timeout:
            dialog = xbmcgui.Dialog()
            dialog.notification(
                "Timeout",
                "Request to Invidious API exceeded timeout",
                "error"
            )

    @classmethod
    def from_argv(cls):
        base_url = sys.argv[0]
        addon_handle = int(sys.argv[1])
        args = parse_qs(sys.argv[2][1:])

        return cls(base_url, addon_handle, args)
