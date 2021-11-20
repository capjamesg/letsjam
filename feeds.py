from feedgen.feed import FeedGenerator
import json
import os

def create_feeds(site_config):
    feeds = (
        ("bookmarks.jf2", "James' Coffee Blog - Bookmarks", "bookmarks"),
        ("likes.jf2", "James' Coffee Blog - Likes", "likes"),
        ("replies.jf2", "James' Coffee Blog - Replies", "webmentions"),
        ("bookmarks.json", "James' Coffee Blog - Bookmarks", "bookmarks"),
        ("likes.json", "James' Coffee Blog - Likes", "likes"),
        ("replies.json", "James' Coffee Blog - Replies", "webmentions"),
        ("bookmarks.xml", "James' Coffee Blog - Bookmarks", "bookmarks"),
        ("likes.xml", "James' Coffee Blog - Likes", "likes"),
        ("replies.xml", "James' Coffee Blog - Replies", "webmentions"),
        ("posts.jf2", "James' Coffee Blog - Posts", "posts"),
        ("posts.json", "James' Coffee Blog - Posts", "posts"),
        ("posts.xml", "James' Coffee Blog - Posts", "posts")
    )

    os.makedirs("_site/feeds")

    for feed_name, feed_title, group in feeds:
        print("Creating feed: " + feed_name)

        if feed_name.endswith(".jf2"):
            full_jf2_feed = {
                "type": "feed",
                "items": []
            }
            for post in site_config[group][:-10]:
                entry = {
                    "type": "entry",
                    "url": post["url"],
                    "category": post["categories"],
                    "author": {
                        "url": "https://jamesg.blog",
                        "name": "James' Coffee Blog",
                        "photo": "https://jamesg.blog/assets/coffeeshop.jpg"
                    },
                    "post-type": "post"
                }

                if post.get("image"):
                    entry["image"] = post["image"]

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
            full_json_feed = {
                "feed_url": "https://jamesg.blog/posts.json",
                "title": feed_title,
                "home_page_url": "https://jamesg.blog",
                "author": {
                    "url": "https://jamesg.blog",
                    "avatar": "https://jamesg.blog/assets/coffeeshop.jpg"
                },
                "version": "https://jsonfeed.org/version/1",
                "items": []
            }
            for post in site_config[group][:-10]:
                entry = {
                    "url": post["url"],
                    "id": post["url"],
                    "author": {
                        "url": "https://jamesg.blog",
                        "name": "James' Coffee Blog"
                    }
                }
                
                if post.get("image"):
                    entry["image"] = post["image"]

                if post.get("title"):
                    entry["title"] = post["title"]
                else:
                    entry["title"] = post["url"]

                full_json_feed["items"].append(entry)

            with open("_site/feeds/" + feed_name, "w+") as file:
                file.write(json.dumps(full_json_feed))

        elif feed_name.endswith(".xml"):
            fg = FeedGenerator()
            
            fg.id("https://jamesg.blog")
            fg.title(feed_title)
            fg.author(name=feed_title)
            fg.link(href="https://jamesg.blog", rel="self")
            fg.logo("https://jamesg.blog/favicon.ico")
            fg.subtitle(feed_title)
            fg.description(feed_title)
            fg.language("en")

            for post in site_config[group][:-10]:
                fe = fg.add_entry()

                fe.id(post["url"])

                if post.get("title"):
                    fe.title(post["title"])
                else:
                    fe.title(post["url"])
                    
                fe.link(href=post["url"])
                fe.description(post["excerpt"])
                fe.author(name="James' Coffee Blog")
                
                if post.get("image"):
                    fe.enclosure(post["image"], 0, "image/jpeg")

            with open("_site/feeds/" + feed_name, "w+") as file:
                feed_to_save = str(fg.rss_str(pretty=True))

                file.write(feed_to_save)