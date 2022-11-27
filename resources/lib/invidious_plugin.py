from datetime import datetime

import requests
import sys
import json
from urllib.parse import urlencode
from urllib.parse import parse_qs

import xbmc
import xbmcgui
import xbmcaddon
import xbmcplugin
import xbmcvfs

import invidious_api
import inputstreamhelper

class InvidiousPlugin:
    # special lists provided by the Invidious API
    SPECIAL_LISTS = ("trending", "popular")
    FOLLOWING_FILENAME = "following.json"

    # Class init
    def __init__(self, base_url, addon_handle, args):
        self.base_url = base_url
        self.addon_handle = addon_handle
        self.addon = xbmcaddon.Addon()
        self.args = args
        self.path = xbmcvfs.translatePath(self.addon.getAddonInfo('profile'))
        self.following_path = self.path + self.FOLLOWING_FILENAME

        instance_url = xbmcplugin.getSetting(self.addon_handle, "instance_url")
        self.api_client = invidious_api.InvidiousAPIClient(instance_url)

    # Utility functions
    def build_url(self, action, **kwargs):
        if not action:
            raise ValueError("you need to specify an action")

        kwargs["action"] = action

        return self.base_url + "?" + urlencode(kwargs)

    def add_directory_item(self, *args, **kwargs):
        xbmcplugin.addDirectoryItem(self.addon_handle, *args, **kwargs)
        
    def end_of_directory(self):
        xbmcplugin.endOfDirectory(self.addon_handle)

    # Menu functions
    def display_main_menu(self):
        def add_list_item(label, path):
            listitem = xbmcgui.ListItem(label, path=path, )
            self.add_directory_item(url=self.build_url(path), listitem=listitem, isFolder=True)
        
        # video search item
        add_list_item(self.addon.getLocalizedString(30008), "search")

        for special_list_name in self.__class__.SPECIAL_LISTS:
            label = special_list_name[0].upper() + special_list_name[1:]
            add_list_item(label, special_list_name)

        add_list_item(self.addon.getLocalizedString(30009), "show_following")

        self.end_of_directory()

    def display_search_results(self, results):
        for result in results:
            if result.type == "video":
                list_item = xbmcgui.ListItem(result.title)
                list_item.setArt({
                    "thumb": result.thumbnail_url
                })

                datestr = datetime.utcfromtimestamp(result.published).date().isoformat()

                list_item.setInfo("video", {
                    "title": result.title,
                    "mediatype": "video",
                    "plot": result.description,
                    "credits": result.author,
                    "date": datestr,
                    "dateadded": datestr,
                })

                # if this is NOT set, the plugin is called with an invalid handle when trying to play this item
                # seriously, Kodi? come on...
                # https://forum.kodi.tv/showthread.php?tid=173986&pid=1519987#pid1519987
                list_item.setProperty("IsPlayable", "true")

                url = self.build_url("play_video", video_id=result.video_id)

                self.add_directory_item(url=url, listitem=list_item)

            elif result.type == "channel":
                list_item = xbmcgui.ListItem(result.name)
                list_item.setArt({
                    "thumb": result.thumbnail_url
                })

                list_item.setProperty("IsPlayable", "true")

                url = self.build_url("show_channel", channel_id=result.channel_id)
                if not self.is_following(result.channel_id):
                    follow_url = self.build_url("follow", channel_id=result.channel_id, name=result.name, thumbnail_url=result.thumbnail_url)
                    list_item.addContextMenuItems([(self.addon.getLocalizedString(30010), 'RunPlugin(' + follow_url + ')')])
                else:
                    unfollow_url = self.build_url("unfollow", channel_id=result.channel_id)
                    list_item.addContextMenuItems([(self.addon.getLocalizedString(30011), 'RunPlugin(' + unfollow_url + ')')])
                
                self.add_directory_item(url=url, listitem=list_item, isFolder=True)

        self.end_of_directory()

    def search(self):
        # query search terms with a dialog
        dialog = xbmcgui.Dialog()
        search_input = dialog.input(self.addon.getLocalizedString(30001), type=xbmcgui.INPUT_ALPHANUM)

        # search for the terms on Invidious
        results = self.api_client.search(search_input)

        # for result in results:
        #     xbmc.log(str(result), xbmc.LOGINFO)


        # assemble menu with the results
        self.display_search_results(results)

    def display_channel(self, channel_id):
        results = self.api_client.fetch_channel_list(channel_id)

        self.display_search_results(results)

    def play_video(self, id):
        # TODO: add support for adaptive streaming
        video_info = self.api_client.fetch_video_information(id)

        listitem = None

        # check if playback via MPEG-DASH is possible
        if "dashUrl" in video_info:
            is_helper = inputstreamhelper.Helper("mpd")
            
            if is_helper.check_inputstream():
                listitem = xbmcgui.ListItem(path=video_info["dashUrl"])
                listitem.setProperty("inputstream", is_helper.inputstream_addon)
                listitem.setProperty("inputstream.adaptive.manifest_type", "mpd")

        # as a fallback, we use the first oldschool stream
        if listitem is None:
            url = video_info["formatStreams"][0]["url"]
            # it's pretty complicated to play a video by its URL in Kodi...
            listitem = xbmcgui.ListItem(path=url)

        xbmcplugin.setResolvedUrl(self.addon_handle, succeeded=True, listitem=listitem)

    def follow(self, channel_id, name, thumbnail_url):
        if not xbmcvfs.exists(self.following_path):
            open(self.following_path, "x")
            following = {}
        else:
            file = open(self.following_path, "r")
            following = json.load(file)
            file.close()

        file = open(self.following_path, "w+")
        following[channel_id] = { 'name': name, 'thumbnail': thumbnail_url }
        json.dump(following, file)
        file.close()

        dialog = xbmcgui.Dialog()
        dialog.notification(
            self.addon.getLocalizedString(30012),
            self.addon.getLocalizedString(30014) + " " + name + "."
        )

    def is_following(self, channel_id):
        if not xbmcvfs.exists(self.following_path):
            return False

        file = open(self.following_path, "r")
        following = json.load(file)
        file.close()
        if channel_id in following:
            return True
        else:
            return False

    def unfollow(self, channel_id):
        file = open(self.following_path, "r")
        following = json.load(file)
        file.close()

        dialog = xbmcgui.Dialog()
        if channel_id in following:
            del following[channel_id]
            file = open(self.following_path, "w+")
            json.dump(following, file)
            file.close()
            dialog.notification(
                self.addon.getLocalizedString(30012),
                self.addon.getLocalizedString(30013),
            )
        else:
            dialog.notification(
                self.addon.getLocalizedString(30015),
                self.addon.getLocalizedString(30016),
                "error"
            )


    def display_following(self):
        if not xbmcvfs.exists(self.following_path):
            self.end_of_directory()
            return

        file = open(self.following_path, "r")
        following = json.load(file)

        for channel_id in following:
            channel = following[channel_id]
            list_item = xbmcgui.ListItem(channel["name"])
            list_item.setArt({
                "thumb": channel["thumbnail"]
            })

            list_item.setProperty("IsPlayable", "true")

            url = self.build_url("show_channel", channel_id=channel_id)

            list_item.addContextMenuItems([(self.addon.getLocalizedString(30011), 'RunPlugin(' + self.build_url("unfollow", channel_id=channel_id) + ')')])

            self.add_directory_item(url=url, listitem=list_item, isFolder=True)
        self.end_of_directory()


    def run(self):
        
        action = self.args.get("action", [None])[0]
        # debugging
        xbmc.log("--------------------------------------------", xbmc.LOGDEBUG)
        xbmc.log("base url:" + str(self.base_url), xbmc.LOGDEBUG)
        xbmc.log("handle:" + str(self.addon_handle), xbmc.LOGDEBUG)
        xbmc.log("args:" + str(self.args), xbmc.LOGDEBUG)
        xbmc.log("action:" + str(action), xbmc.LOGDEBUG)
        xbmc.log("--------------------------------------------", xbmc.LOGDEBUG)

        try:

            if not action:
                self.display_main_menu()

            elif action == "search":
                self.search()

            elif action == "show_channel":
                self.display_channel(self.args["channel_id"][0])

            elif action == "play_video":
                self.play_video(self.args["video_id"][0])
            
            elif action == "follow":
                self.follow(self.args["channel_id"][0], self.args["name"][0], self.args["thumbnail_url"][0])

            elif action == "unfollow":
                self.unfollow(self.args["channel_id"][0])

            elif action == "show_following":
                self.display_following()

        except requests.HTTPError as e:
            dialog = xbmcgui.Dialog()
            dialog.notification(
                self.addon.getLocalizedString(30003),
                self.addon.getLocalizedString(30004) + str(e.response.status_code),
                "error"
            )

        except requests.Timeout:
            dialog = xbmcgui.Dialog()
            dialog.notification(
                self.addon.getLocalizedString(30005),
                self.addon.getLocalizedString(30006),
                "error"
            )

    # No clue what this is lol
    @classmethod
    def from_argv(cls):
        base_url = sys.argv[0]
        addon_handle = int(sys.argv[1])
        args = parse_qs(sys.argv[2][1:])

        return cls(base_url, addon_handle, args)
