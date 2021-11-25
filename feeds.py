import json
import os
from feedgen.feed import FeedGenerator

def create_feeds(site_config, posts):
    feeds = (
        ("bookmarks.jf2", "James' Coffee Blog - Bookmarks", "bookmarks"),
        ("likes.jf2", "James' Coffee Blog - Likes", "likes"),
        ("replies.jf2", "James' Coffee Blog - Replies", "webmentions"),
        ("coffee.jf2", "James' Coffee Blog - Coffee Log", "drinking"),
        ("bookmarks.json", "James' Coffee Blog - Bookmarks", "bookmarks"),
        ("likes.json", "James' Coffee Blog - Likes", "likes"),
        ("replies.json", "James' Coffee Blog - Replies", "webmentions"),
        ("coffee.json", "James' Coffee Blog - Coffee Log", "drinking"),
        ("bookmarks.xml", "James' Coffee Blog - Bookmarks", "bookmarks"),
        ("likes.xml", "James' Coffee Blog - Likes", "likes"),
        ("replies.xml", "James' Coffee Blog - Replies", "webmentions"),
        ("coffee.xml", "James' Coffee Blog - Coffee Log", "drinking"),
        ("posts.jf2", "James' Coffee Blog - Posts", "posts"),
        ("posts.json", "James' Coffee Blog - Posts", "posts"),
        ("posts.xml", "James' Coffee Blog - Posts", "posts")
    )

    os.makedirs("_site/feeds")

    for feed_name, feed_title, group in feeds:
        if group == "posts":
            feed_items = posts[:-10]
        else:
            feed_items = site_config[group][:-10]

        print("Creating feed: " + feed_name)

        if feed_name.endswith(".jf2"):
            year, month, day = post["url"].split(".")[:3]

            date_published = "{}-{}-{}T00:00:00-00:00".format(year, month, day)

            full_jf2_feed = {
                "type": "feed",
                "items": []
            }

            for post in feed_items:
                entry = {
                    "type": "entry",
                    "url": site_config["baseurl"] + post["url"],
                    "category": post["categories"],
                    "author": {
                        "url": site_config["baseurl"],
                        "name": site_config["title"],
                        "photo": site_config["avatar"]
                    },
                    "published": date_published,
                    "post-type": "post"
                }

                if post.get("image"):
                    entry["image"] = site_config["baseurl"] + post["image"]

                if post.get("title"):
                    entry["title"] = post["title"]
                else:
                    entry["title"] = post["url"]

                if post.get("content"):
                    entry["content"] = {
                        "text": post["content"]
                    }

                full_jf2_feed["items"].append(entry)

            with open("_site/feeds/" + feed_name, "w+") as file:
                file.write(json.dumps(full_jf2_feed))

        elif feed_name.endswith(".json"):
            year, month, day = post["url"].split(".")[:3]

            date_published = "{}-{}-{}T00:00:00-00:00".format(year, month, day)

            full_json_feed = {
                "feed_url": site_config["baseurl"] + "/" + feed_name,
                "title": feed_title,
                "home_page_url": site_config["baseurl"],
                "author": {
                    "url": site_config["baseurl"],
                    "avatar": site_config["avatar"]
                },
                "version": "https://jsonfeed.org/version/1",
                "items": []
            }
            for post in feed_items:
                entry = {
                    "url": site_config["baseurl"] + post["url"],
                    "id": site_config["baseurl"] + post["url"],
                    "author": {
                        "url": site_config["baseurl"],
                        "name": site_config["author"]
                    },
                    "date_published": date_published
                }
                
                if post.get("image"):
                    entry["image"] = site_config["baseurl"] + post["image"]

                if post.get("title"):
                    entry["title"] = post["title"]
                else:
                    entry["title"] = post["url"]

                full_json_feed["items"].append(entry)

            with open("_site/feeds/" + feed_name, "w+") as file:
                file.write(json.dumps(full_json_feed))

        elif feed_name.endswith(".xml"):
            full_feed = FeedGenerator()
            
            full_feed.id(site_config["baseurl"])
            full_feed.title(feed_title)
            full_feed.author(name=feed_title)
            full_feed.link(href=site_config["baseurl"], rel="self")
            full_feed.logo(site_config["baseurl"] + "/favicon.ico")
            full_feed.subtitle(feed_title)
            full_feed.description(feed_title)
            full_feed.language("en")

            year, month, day = post["url"].split(".")[:3]

            date_published = "{}-{}-{}T00:00:00-00:00".format(year, month, day)

            for post in feed_items:
                feed_entry = full_feed.add_entry()

                feed_entry.id(site_config["baseurl"] + post["url"])

                if post.get("title"):
                    feed_entry.title(post["title"])
                else:
                    feed_entry.title(site_config["baseurl"] + post["url"])
                
                feed_entry.link(href=site_config["baseurl"] + post["url"])
                feed_entry.description(post["excerpt"])
                feed_entry.author(name=site_config["author"])
                feed_entry.published(date_published)
                
                if post.get("image"):
                    feed_entry.enclosure(site_config["baseurl"] + post["image"], 0, "image/jpeg")

            with open("_site/feeds/" + feed_name, "w+") as file:
                feed_to_save = full_feed.rss_str(pretty=False, encoding="utf-8")

                feed_to_save = str(feed_to_save.decode("utf-8"))

                file.write(feed_to_save)