site_config = {
    "title": "Blog Title",
    "posts": [],
    "likes": [],
    "bookmarks": [],
    "replies": [],
    "rsvps": [],
    "baseurl": "https://example.com",
    "webmentions": [],
    "wiki": []
}

BASE_DIR = "."
OUTPUT = "_site"
ALLOWED_SLUG_CHARS = ["-", "/", ".", "_"]

# enable auto-generated page types
# these values must be either True or False, or an error will be thrown

CATEGORY_PAGE_GENERATION = True
PAGINATION_PAGE_GENERATION = True
DATE_ARCHIVE_GENERATION = True
LIST_PAGE_GENERATION = True

FEEDS = (
    ("bookmarks.xml", "Example Blog Posts", "posts", "rss"),
)