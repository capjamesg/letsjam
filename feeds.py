import json
import datetime
import os
from feedgen.feed import FeedGenerator

def get_date_published(url):
    date_published = ""

    if url.count("-") > 2 and url.split("-")[1].isnumeric():
        year, month, day = url.split("-")[:3]

        date_published = f"{year}-{month}-{day}T00:00:00-00:00"

    try:
        formatted_date = datetime.datetime.strptime(date_published, "%Y-%m-%dT%H:%M:%S%z").strftime("%B %d, %Y")
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
            feed_items = posts[:10]
        else:
            feed_items = site_config[group][:10]

        if group == "likes":
            post_type = "like"
        elif group == "webmentions":
            post_type = "reply"
        elif group == "bookmarks":
            post_type = "bookmark"
        elif group == "posts":
            post_type = "post"
        else:
            post_type = "note"

        print("Creating feed: " + feed_name)

        if feed_name.endswith(".jf2"):
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
                    "published": post["date_published"],
                    "post-type": post_type
                }

                image = retrieve_image(post, site_config)

                if image != None:
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
                if post.get("context") and context_url != None:
                    context = post.get("context")

                    entry["refs"] = {
                        "type": "entry",
                        "url": context_url,
                        "content": {
                            "text": context["post_body"]
                        }
                    }

                    if context.get("author_name") and context.get("author_url"):
                        entry["refs"]["author"] = {
                            "type": "card",
                            "url": context["author_url"],
                            "name": context["author_name"]
                        }

                        if context.get("author_image"):
                            entry["refs"]["author"]["photo"] = context["author_image"]

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
                    "content_html": post["content"],
                    "date_published": post["date_published"]
                }

                image = retrieve_image(post, site_config)

                if image != None:
                    entry["image"] = image

                if post.get("categories"):
                    entry["tags"] = post["categories"]

                if post.get("title"):
                    entry["title"] = post["title"]

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

            for post in feed_items:
                feed_entry = full_feed.add_entry()

                feed_entry.id(site_config["baseurl"] + post["url"])

                if post.get("title"):
                    feed_entry.title(post["title"])
                else:
                    feed_entry.title(site_config["baseurl"] + post["url"])
                
                feed_entry.link(link={"href": site_config["baseurl"] + post["url"]})
                feed_entry.description(post["excerpt"])
                feed_entry.author({"name": site_config["author"]})

                if post["date_published"] != "":
                    try:
                        feed_entry.published(post["date_published"])
                    except:
                        continue

                image = retrieve_image(post, site_config)
                
                if image != None:
                    feed_entry.enclosure(image, 0, "image/jpeg")

                feed_entry.content(post["content"])

            try:
                with open("_site/feeds/" + feed_name, "w+") as file:
                    feed_to_save = full_feed.rss_str(pretty=False, encoding="utf-8")

                    feed_to_save = str(feed_to_save.decode("utf-8"))

                    file.write(feed_to_save)
            except Exception as e:
                print(e)