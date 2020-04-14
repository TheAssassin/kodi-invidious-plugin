import time
from collections import namedtuple

import requests

SearchResult = namedtuple("SearchResult", ["video_id", "title", "author", "description", "thumbnail_url"])


class InvidiousAPIClient:
    def __init__(self, instance_url):
        self.instance_url = instance_url.rstrip("/")

    def make_get_request(self, *path, **params):
        base_url = self.instance_url + "/api/v1/"

        url_path = "/".join(path)

        while "//" in url_path:
            url_path = url_path.replace("//", "/")

        assembled_url = base_url + url_path

        print("========== request started ==========")
        start = time.time()
        response = requests.get(assembled_url, params=params, timeout=5)
        end = time.time()
        print("========== request finished in", end - start, "s ==========")

        response.raise_for_status()

        return response

    def search(self, *terms):
        params = {
            "q": " ".join(terms),
            "sort_by": "upload_date",
        }

        response = self.make_get_request("search", **params)

        data = response.json()

        for video in data:
            for thumb in video["videoThumbnails"]:
                # high appears to be ~480x360, which is a reasonable trade-off
                # works well on 1080p
                if thumb["quality"] == "high":
                    thumbnail_url = thumb["url"]
                    break

            # as a fallback, we just use the last one in the list (which is usually the lowest quality)
            else:
                thumbnail_url = video["videoThumbnails"][-1]["url"]

            yield SearchResult(
                video["videoId"],
                video["title"],
                video["author"],
                video["description"],
                thumbnail_url
            )

    def fetch_video_information(self, video_id):
        response = self.make_get_request("videos/", video_id)

        data = response.json()

        return data
