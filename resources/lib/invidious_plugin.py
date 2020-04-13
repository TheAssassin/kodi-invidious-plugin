from urllib import urlencode

import xbmcgui
import xbmcplugin

import invidious_api


class InvidiousPlugin:
    def __init__(self, base_url, addon_handle, args):
        self.base_url = base_url
        self.addon_handle = addon_handle
        self.args = args

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
        results = invidious_api.search(search_input)

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

            url = self.build_url("video", id=video.video_id)

            self.add_directory_item(url=url, listitem=list_item)

        self.end_of_directory()

    def play_video(self, id):
        # TODO: add support for adaptive streaming
        url = invidious_api.get_stream_url_for_id(id)

        # it's pretty complicated to play a video in Kodi
        listitem = xbmcgui.ListItem(path=url)
        xbmcplugin.setResolvedUrl(self.addon_handle, True, listitem=listitem)

    def display_main_menu(self):
        # search item
        listitem = xbmcgui.ListItem("Search", path="search")
        self.add_directory_item(url=self.build_url("search"), listitem=listitem, isFolder=True)

        self.end_of_directory()

    def run(self):
        """
        Web application style router. Uses querystring for everything, which is pretty oldschool CGI-like stuff.
        """

        action = self.args.get("action", [None])[0]

        # debugging
        print("--------------------------------------------")
        print("base url:", self.base_url)
        print("handle:", self.addon_handle)
        print("args:", self.args)
        print("action:", action)
        print("--------------------------------------------")

        if not action:
            self.display_main_menu()

        elif action == "search":
            self.display_search()

        elif action == "video":
            self.play_video(self.args["id"][0])

        else:
            raise RuntimeError("unknown action " + action)
