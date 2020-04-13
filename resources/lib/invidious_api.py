from collections import namedtuple

import requests

SearchResult = namedtuple("SearchResult", ["video_id", "title", "author", "description", "thumbnail_url"])


def search(*terms):
    params = {
        "q": " ".join(terms),
        "sort_by": "upload_date",
    }

    response = requests.get("https://invidio.us/api/v1/search", params=params)
    response.raise_for_status()

    data = response.json()

    for video in data:
        yield SearchResult(
            video["videoId"],
            video["title"],
            video["author"],
            video["description"],
            video["videoThumbnails"][0]["url"]
        )


def get_stream_url_for_id(video_id):
    response = requests.get("https://invidio.us/api/v1/videos/" + video_id)
    response.raise_for_status()

    data = response.json()

    return data["formatStreams"][0]["url"]
