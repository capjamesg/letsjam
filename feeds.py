from feedgen.feed import FeedGenerator
import json
import os

def create_feeds(site_config):
    feeds = [
        "bookmarks.jf2",
        "likes.jf2",
        "replies.jf2",
        "bookmarks.json",
        "likes.json",
        "replies.json",
        "bookmarks.xml",
        "likes.xml",
        "replies.xml"
    ]

    os.makedirs("_site/feeds")

    for f in feeds:
        print("Creating feed: " + f)
        
        if f.endswith(".jf2"):
            full_jf2_feed = {
                "type": "feed",
                "items": []
            }
            for post in site_config["posts"][:-10]:
                entry = {
                    "type": "entry",
                    "name": post["title"],
                    "url": post["url"],
                    "image": post["image"],
                    "category": post["category"],
                    "content": {
                        "text": post["content"]
                    },
                    "author": {
                        "url": "https://jamesg.blog",
                        "name": "James' Coffee Blog",
                        "photo": "https://jamesg.blog/assets/coffeeshop.jpg"
                    },
                    "post-type": "post"
                }
                full_jf2_feed["items"].append(entry)

            with open("_site/feeds/" + f.replace(".jf2", ".xml"), "w+") as file:
                file.write(json.dumps(full_jf2_feed))

        elif f.endswith(".json"):
            full_json_feed = {
                "feed_url": "https://jamesg.blog/posts.json",
                "title": "James' Coffee Blog",
                "home_page_url": "https://jamesg.blog",
                "author": {
                    "url": "https://jamesg.blog",
                    "avatar": "https://jamesg.blog/assets/coffeeshop.jpg"
                },
                "version": "https://jsonfeed.org/version/1",
                "items": []
            }
            for post in site_config["posts"][:-10]:
                entry = {
                    "title": post["title"],
                    "url": post["url"],
                    "id": post["url"],
                    "image": post["image"],
                    "author": {
                        "url": "https://jamesg.blog",
                        "name": "James' Coffee Blog"
                    }
                }
                full_json_feed["items"].append(entry)

            with open("_site/feeds/" + f.replace(".json", ".xml"), "w+") as file:
                file.write(json.dumps(full_json_feed))

        elif f.endswith(".xml"):
            fg = FeedGenerator()
            
            fg.id("https://jamesg.blog")
            fg.title("James'Coffee Blog")
            fg.author(name="James' Coffee Blog")
            fg.link(href="https://jamesg.blog", rel="self")
            fg.logo("https://jamesg.blog/favicon.ico")
            fg.subtitle("James' Coffee Blog")
            fg.description("James' Coffee Blog")
            fg.language("en")

            for post in site_config["posts"][:-10]:
                fe = fg.add_entry()

                fe.id(post["url"])
                fe.title(post["title"])
                fe.link(href=post["url"])
                fe.description(post["excerpt"])
                fe.author(name="James' Coffee Blog")
                fe.enclosure(post["image"], 0, "image/jpeg")

            with open("_site/feeds/" + f, "w+") as file:
                feed_to_save = str(fg.rss_str(pretty=True))

                file.write(feed_to_save)