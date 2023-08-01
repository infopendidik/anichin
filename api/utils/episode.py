from .parsing import Parsing
from urllib.parse import urlparse, urlencode, parse_qsl
from dotenv import load_dotenv
from base64 import b64decode
from time import strptime
import re

load_dotenv()


class Episode(Parsing):
    def __init__(self, slug):
        super().__init__()
        self.slug = slug

    def __get_info(self):
        return self.get_parsed_html(self.slug)

    def __get_name(self, content):
        return content.find("h2", {"itemprop": "partOfSeries"}).text.strip()

    def __get_genres(self, content):
        genres = content.find("div", {"class": "genxed"}).find_all("a")
        return list(map(lambda x: x.text, genres))

    def __get_info_details(self, content):
        info = (
            content.find("div", {"class": "info-content"})
            .find("div", {"class": "spe"})
            .find_all("span")
        )
        info = dict(
            map(
                lambda x: [x[0].strip().lower().replace(" ", "_"), x[1].strip()],
                filter(
                    lambda x: x[0] != "",
                    map(lambda x: x.split(":"), map(lambda x: x.text, info)),
                ),
            )
        )
        return info

    def __get_rating(self, content):
        rating = content.find("div", {"class": "rating"}).find("strong").text
        return rating.split(" ")[1]

    def __get_sinopsis(self, data):
        sinopsis = data.find("div", {"class": "desc mindes"}).get_text(strip=True)
        return sinopsis

    def __get_episodes(self, data):
        result = []
        episodes = data.find("div", {"class": "episodelist"}).find("ul").find_all("li")
        for item in episodes:
            name = item.find("img", {"class": "ts-post-image"}).get("title")
            slug = urlparse(item.find("a")["href"]).path.lstrip("/")
            tt = item.find("div", {"class": "playinfo"})
            span = tt.find("span")
            episode_headline = span.get_text(strip=True) if span else ""
            if episode_headline.startswith("Eps"):
                parts = episode_headline.split(" - ")
                eps = re.sub("[^0-9]", "", parts[0])
                subtitle = parts[1].strip() if len(parts) > 2 else None
                date = (
                    parts[2].strip() if len(parts) > 2 else parts[1].strip()
                )  # July 31 2023
                date = strptime(date.replace(",", ""), "%B %d %Y")
                # day, month, year
                date = f"{date.tm_mon}/{date.tm_mday}/{date.tm_year}"
            res = dict(
                name=name,
                slug=slug,
                subtitle=subtitle,
                date=date,
                episode=eps,
            )
            result.append(res)
        return result

    def __get_video(self, data):
        video = data.find("select", {"class": "mirror"})
        if video:
            video = video.find_all("option")
            video = list(map(lambda x: self.__bs64(x["value"], x.text), video))
            return list(filter(lambda x: x, video))
        return {"error": "Video not found"}

    def __bs64(self, data, name=""):
        if data:
            decode = b64decode(data).decode("utf-8")
            content = self.parsing(decode).find("iframe")
            if content:
                return dict(
                    name=name.strip(),
                    url=content["src"],
                )
        return None

    def to_json(self):
        data = self.__get_info()
        content = data.find("div", {"class": "infox"})
        player_list = self.__get_video(data)
        name = self.__get_name(content)
        genres = self.__get_genres(content)
        info = self.__get_info_details(content)
        rating = self.__get_rating(content)
        sinopsis = self.__get_sinopsis(data)
        episode = self.__get_episodes(data)
        info = {
            **info,
            "name": name,
            "genre": genres,
            "rating": rating,
            "sinopsis": sinopsis,
            "episode": episode,
            "players": player_list,
        }
        return dict(result=info, source=self.history_url)
