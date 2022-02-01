site_config = {
    "title": "James' Coffee Blog",
    "posts": [],
    "categories": {},
    "months": [],
    "years": [],
    "likes": [],
    "bookmarks": [],
    "replies": [],
    "reposts": [],
    "rsvps": [],
    "baseurl": "https://jamesg.blog",
    "pages": [],
    "replies": [],
    "notes": [],
    "status": [],
    "ate": []
}

BASE_DIR = "."
OUTPUT = "_site"
ALLOWED_SLUG_CHARS = ["-", "/", ".", "_"]

FEEDS = [
    ("bookmarks.jf2", "James' Coffee Blog - Bookmarks", "bookmarks", "jf2"),
    ("likes.jf2", "James' Coffee Blog - Likes", "likes", "jf2"),
    ("replies.jf2", "James' Coffee Blog - Replies", "replies", "jf2"),
    ("bookmarks.json", "James' Coffee Blog - Bookmarks", "bookmarks", "json"),
    ("likes.json", "James' Coffee Blog - Likes", "likes", "json"),
    ("replies.json", "James' Coffee Blog - Replies", "replies", "json"),
    ("bookmarks.xml", "James' Coffee Blog - Bookmarks", "bookmarks", "rss"),
    ("likes.xml", "James' Coffee Blog - Likes", "likes", "rss"),
    ("replies.xml", "James' Coffee Blog - Replies", "replies", "rss"),
    ("posts.jf2", "James' Coffee Blog - Posts", "posts", "jf2"),
    ("posts.json", "James' Coffee Blog - Posts", "posts", "json"),
    ("posts.xml", "James' Coffee Blog - Posts", "posts", "rss"),
    ("notes.json", "James' Coffee Blog - Notes", "notes", "json"),
    ("notes.xml", "James' Coffee Blog - Notes", "notes", "rss"),
]