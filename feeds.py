import datetime
import json
import os
import re

from bs4 import BeautifulSoup
from feedgen.feed import FeedGenerator

from config import FEEDS


def get_published_date(url, post_type, published):
    published = ""

    if post_type == "article":
        if url.count("-") > 2 and url.split("-")[1].isnumeric():
            year, month, day = url.split("-")[:3]

            published = f"{year}-{month}-{day} 00:00:00-00:00"

    try:
        formatted_date = datetime.datetime.strptime(published, "%Y-%m-%d %H:%M:%S%z")
    except:
        formatted_date = ""

    return formatted_date


def retrieve_image(post, site_config):
    if post.get("image") and type(post["image"]) is str:
        image = site_config["baseurl"] + post["image"]
    elif post.get("image") and type(post["image"]) is list:
        image = site_config["baseurl"] + post["image"][0]
    elif post.get("image") and type(post["image"]) is dict:
        image = site_config["baseurl"] + post["image"].get("value")
    else:
        image = None

    return image


def create_feeds(site_config, posts):
    feeds = FEEDS

    os.makedirs("_site/feeds")

    for feed_name, feed_title, group, feed_type in feeds:
        if group == "posts":
            feed_items = posts[:10]
        else:
            feed_items = site_config[group][:10]

        if group == "likes":
            post_type = "like"
        elif group == "replies":
            post_type = "reply"
        elif group == "bookmarks":
            post_type = "bookmark"
        elif group == "posts":
            post_type = "post"
        else:
            post_type = "note"

        print("Creating feed: " + feed_name)

        if feed_type == "jf2":
            full_jf2_feed = {"type": "feed", "items": []}

            for post in feed_items:
                parsed = BeautifulSoup(post["content"], "lxml")

                as_text = parsed.get_text()

                hashtags = re.findall(r"#(\w+)", as_text)

                entry = {
                    "type": "entry",
                    "url": site_config["baseurl"] + post["url"],
                    "category": post["categories"],
                    "author": {
                        "url": site_config["baseurl"],
                        "name": site_config["title"],
                        "photo": site_config["avatar"],
                    },
                    "published": post["full_date"],
                    "post-type": post_type,
                }

                image = retrieve_image(post, site_config)

                if image is not None:
                    entry["image"] = image

                if post.get("like-of"):
                    entry["like-of"] = post["like-of"]
                    context_url = post["like-of"]
                elif post.get("in-reply-to"):
                    entry["in-reply-to"] = post["in-reply-to"]
                    context_url = post["in-reply-to"]
                elif post.get("bookmark-of"):
                    entry["bookmark-of"] = post["bookmark-of"]
                    context_url = post["bookmark-of"]
                else:
                    context_url = None

                # show reply context in feed item
                if (
                    post.get("context")
                    and context_url is not None
                    and post["context"].get("post_body")
                ):
                    context = post.get("context")

                    entry["refs"] = {
                        "type": "entry",
                        "url": context_url,
                        "content": {"text": context["post_body"]},
                    }

                    if context.get("author_name") and context.get("author_url"):
                        entry["refs"]["author"] = {
                            "type": "card",
                            "url": context["author_url"],
                            "name": context["author_name"],
                        }

                        if context.get("author_image"):
                            entry["refs"]["author"]["photo"] = context["author_image"]

                if post.get("title"):
                    entry["title"] = post["title"]
                else:
                    entry["title"] = post["url"]

                if hashtags:
                    entry["category"] = hashtags

                if post.get("categories"):
                    entry["category"] = post["categories"]

                if post.get("content"):
                    entry["content"] = {"text": post["content"]}

                images = parsed.find_all("img")

                entry["photo"] = [photo.src for photo in images]

                full_jf2_feed["items"].append(entry)

            with open("_site/feeds/" + feed_name, "w+") as file:
                file.write(json.dumps(full_jf2_feed))

        elif feed_type == "json":
            full_json_feed = {
                "version": "https://jsonfeed.org/version/1.1",
                "feed_url": site_config["baseurl"] + "/feeds/" + feed_name,
                "title": feed_title,
                "home_page_url": site_config["baseurl"],
                "authors": [
                    {"url": site_config["baseurl"], "avatar": site_config["avatar"]}
                ],
                "items": [],
            }
            for post in feed_items:
                parsed = BeautifulSoup(post["content"], "lxml")

                as_text = parsed.get_text()

                hashtags = re.findall(r"#(\w+)", as_text)

                entry = {
                    "url": site_config["baseurl"] + post["url"],
                    "id": site_config["baseurl"] + post["url"],
                    "authors": [
                        {"url": site_config["baseurl"], "name": site_config["author"]}
                    ],
                    "content_html": post["content"],
                    "content_text": as_text,
                    "date_published": post["full_date"],
                }

                image = retrieve_image(post, site_config)

                if image is not None:
                    entry["image"] = image

                if post.get("categories"):
                    entry["tags"] = post["categories"]

                if hashtags:
                    entry["tags"] = hashtags

                if post.get("title") and group == "posts":
                    entry["title"] = post["title"]

                images = parsed.find_all("img")

                if images and len(images) > 0:
                    entry["image"] = images[0]["src"]

                full_json_feed["items"].append(entry)

            with open("_site/feeds/" + feed_name, "w+") as file:
                file.write(json.dumps(full_json_feed))

        elif feed_type == "rss":
            full_feed = FeedGenerator()

            full_feed.id(site_config["baseurl"])
            full_feed.title(feed_title)
            full_feed.author(name=feed_title)
            full_feed.link(href=site_config["baseurl"], rel="self")
            full_feed.logo(site_config["baseurl"] + "/favicon.ico")
            full_feed.subtitle(feed_title)
            full_feed.description(feed_title)
            full_feed.language("en")

            feed_items.reverse()

            for post in feed_items:
                feed_entry = full_feed.add_entry()

                feed_entry.id(site_config["baseurl"] + post["url"])

                if post.get("title"):
                    feed_entry.title(post["title"])
                else:
                    feed_entry.title(site_config["baseurl"] + post["url"])

                feed_entry.link(link={"href": site_config["baseurl"] + post["url"]})
                feed_entry.description(post["content"])
                feed_entry.author({"name": site_config["author"]})

                if post["full_date"] != "":
                    try:
                        feed_entry.published(post["full_date"])
                    except:
                        continue

                image = retrieve_image(post, site_config)

                if image is not None:
                    feed_entry.enclosure(image, 0, "image/jpeg")

                feed_entry.content(post["content"])

                print(feed_entry.author)

            try:
                with open("_site/feeds/" + feed_name, "w+") as file:
                    feed_to_save = full_feed.rss_str(pretty=False, encoding="utf-8")

                    feed_to_save = str(feed_to_save.decode("utf-8"))

                    file.write(feed_to_save)
            except Exception as e:
                print(e)
