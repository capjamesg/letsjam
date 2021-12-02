import os
import sys
import shutil
import datetime
import frontmatter
import markdown
import jinja2
import yaml
from bs4 import BeautifulSoup
import feeds
import create_archives
from config import BASE_DIR, OUTPUT, ALLOWED_SLUG_CHARS

start_time = datetime.datetime.now()

post_directory = "_posts"

# remove _site dir and all files in it
shutil.rmtree("_site", ignore_errors=True)

# create _site dir
if not os.path.exists("_site"):
    os.makedirs("_site")

posts = sorted(
    os.listdir("_posts"),
    key=lambda s: "".join([char for char in s if char.isnumeric()])
)

def create_non_post_files(all_directories, pages_created_count, site_config):
    """
        Create all individual files (i.e. about.html) that aren't posts.
    """
    do_not_process = ("_posts", "_layouts", "_site", "assets", "_includes", "_drafts")

    for directory in all_directories:
        directory_name = BASE_DIR + "/" + directory

        # don't process certain directories
        if directory.startswith(do_not_process) or os.path.isfile(directory_name) or directory.startswith("."):
            continue

        all_files = os.listdir(directory_name)

        for file in sorted(all_files, key=lambda s: "".join([char for char in s if char.isnumeric()])):
            f = directory_name + "/" + file

            if os.path.isdir(f):
                continue

            file_name = f.replace(directory_name, "")

            extension = file_name.split(".")[-1]

            # do not copy dotfiles into site
            # also do not create archive.html file as that is created later

            if file_name.startswith("."):
                continue

            # the archive page is created separately in the create_archive files
            if file_name == "/archive.html":
                continue

            if extension in ("md", "html") and not os.path.isdir(f):
                process_page(directory_name, f, site_config)
            elif extension not in ("py", "pyc", "cfg") and not os.path.isdir(f):
                shutil.copy(f, OUTPUT + "/" + file_name)

            pages_created_count += 1

    return site_config, pages_created_count

def create_template(path, **kwargs):
    """
        Create a full page from a jinja2 template and its associated front matter.
    """

    template_front_matter = frontmatter.load(path)

    loader = jinja2.FileSystemLoader(searchpath="./")

    template = jinja2.Environment(loader=loader)

    # register filter
    template.filters["long_date"] = create_archives.long_date
    template.filters["date_to_xml_string"] = create_archives.date_to_xml_string
    template.filters["archive_date"] = create_archives.archive_date

    if path.endswith(".md"):
        template_front_matter.content = markdown.markdown(template_front_matter.content)

    new_template = template.from_string(template_front_matter.content)

    if len(sys.argv) > 1 and sys.argv[1] == "--retro" \
            and template_front_matter.metadata.get("layout") \
                and template_front_matter.metadata["layout"] == "default":
        template_front_matter.metadata["layout"] = "retro"

    if template_front_matter.metadata.get("layout"):
        parent_front_matter = frontmatter.load("_layouts/" + template_front_matter.metadata["layout"] + ".html")
        parent_template = template.from_string(parent_front_matter.content)

        if len(sys.argv) > 1 and sys.argv[1] == "--retro" \
                and parent_front_matter.metadata.get("layout") \
                    and parent_front_matter.metadata["layout"] == "default":
            parent_front_matter.metadata["layout"] = "retro"

        new_template = parent_template.render(content=new_template.render(kwargs), **kwargs)

        kwargs["content"] = new_template

        if parent_front_matter.metadata.get("layout"):
            template = create_template("_layouts/" + parent_front_matter.metadata["layout"] + ".html", **kwargs)
        else:
            template = new_template
    else:
        template = new_template.render(kwargs) 

    if len(sys.argv) > 1 and sys.argv[1] == "--retro":
        template = template.replace('<div id="main">', '<div id="main" class="flex_right_home">')
    
    return template

def process_page(directory_name, file_name, site_config, page_type=None, previous_page=None, next_post=None, next_post_url=None):
    front_matter = frontmatter.load(file_name)
    
    if previous_page:
        front_matter.metadata["previous"] = {
            "title": frontmatter.load(previous_page).metadata["title"],
            "url": previous_page.replace(directory_name, "")
        }

    else:
        front_matter.metadata["previous"] = {
            "title": "",
            "url": ""
        }

    if next_post is not None:
        front_matter.metadata["next"] = {
            "title": next_post["title"],
            "url": next_post_url
        }
    else:
        front_matter.metadata["next"] = {
            "title": "",
            "url": ""
        }

    if front_matter.metadata == {}:
        return site_config

    # do not process pages with no content
    if len(front_matter.content) == 0:
        return site_config

    if front_matter.metadata.get("categories") is None:
        front_matter.metadata["categories"] = []

    if file_name.endswith(".md"):
        front_matter.content = markdown.markdown(front_matter.content)

    soup = BeautifulSoup(front_matter.content, "html.parser")

    if soup.find_all("p") and len(soup.find_all("p")) > 2:
        # first paragraph sentences will be considered "excerpt" value
        front_matter.metadata["excerpt"] = " ".join([sentence.text for sentence in soup.find_all("p")[:1]])

        # use first sentence for meta description
        front_matter.metadata["meta_description"] = "".join(front_matter.metadata["excerpt"].split(". ")[0]) + "..."
    else:
        # used as a fallback
        front_matter.metadata["excerpt"] = front_matter.content

    if front_matter.metadata["layout"].rstrip("s").lower() in ["like", "bookmark", "repost", "webmention", "note"]:
        site_config[front_matter.metadata["layout"].rstrip("s")] = site_config[front_matter.metadata["layout"].rstrip("s")] + [front_matter.metadata]

    print("Generating " + file_name)

    if page_type == "post":
        path_to_save = OUTPUT + "/" + file_name.replace(BASE_DIR, "").strip("/")

        file = file_name.split("/")[-1]

        year = file.split("-")[0]
        month = file.split("-")[1]
        day = file.split("-")[2]

        # if post published after today, do not generate it
        # this ensures content scheduled for the future is not published
        if datetime.datetime.strptime(year + "-" + month + "-" + day, "%Y-%m-%d") > datetime.datetime.now():
            return site_config

        site_config["years"].append(year)
        site_config["months"].append(month)

        front_matter.metadata["date"] = datetime.datetime.strptime(year + "-" + month + "-" + day, "%Y-%m-%d")

        if not os.path.exists(OUTPUT + "/" + year + "/" + month + "/" + day):
            os.makedirs(OUTPUT + "/" + year + "/" + month + "/" + day)
        
        path_to_save = OUTPUT + "/" + year + "/" + month + "/" + day + "/" + "-".join(file.split("-")[3:]).split(".")[0] + "/index.html"
    else:
        path_to_save = OUTPUT + "/" + file_name.strip("/").replace("templates/", "").replace("_", "").replace(".md", "") + "/index.html"

        if path_to_save.endswith("html") and not path_to_save.endswith(".html"):
            path_to_save = path_to_save.replace("html", ".html")
        
    if front_matter.get("permalink") and front_matter.get("permalink").endswith(".html"):
        path_to_save = OUTPUT + front_matter.get("permalink").rstrip("/")
    elif front_matter.get("permalink"):
        path_to_save = OUTPUT + front_matter.get("permalink").rstrip("/") + "/" + "index.html"

    url = path_to_save.replace(OUTPUT, "").replace("/index.html", "/").replace("/templates/", "").replace("index.html", "/").replace(".html", "").replace("./", "")
        
    front_matter.metadata["url"] = url
    front_matter.metadata["slug"] = url
    front_matter.metadata["date_published"] = feeds.get_date_published(file_name.split("/")[-1])
    front_matter.metadata["content"] = front_matter.content

    rendered_string = create_template(
        file_name,
        site=site_config,
        page=front_matter.metadata,
        paginator=None
    )

    dir_to_save = "/".join(path_to_save.split("/")[:-1])

    if not os.path.exists(dir_to_save):
        os.makedirs(dir_to_save)

    with open(path_to_save, "w+") as file:
        file.write(rendered_string)

    if site_config and site_config.get("pages"):
        site_config["pages"] = site_config["pages"] + [front_matter.metadata["url"]]
    elif site_config:
        site_config["pages"] = [front_matter.metadata["url"]]

    if page_type == "post":
        site_config["posts"] = site_config["posts"] + [front_matter.metadata]

        for category in front_matter.metadata["categories"]:
            if "(Series)" in category:
                site_config["series_posts"].append([front_matter.metadata["categories"][0], file_name.replace("_posts", ""), front_matter.metadata["url"]])
                
            if site_config["categories"].get(category) is None:
                site_config["categories"][category] = [front_matter.metadata]
            else:
                site_config["categories"][category] = site_config["categories"][category] + [front_matter.metadata]

    groups = (
        ("Like", "likes"),
        ("Bookmark", "bookmarks"),
        ("Webmention", "webmentions"),
        ("Reply", "webmentions"),
        ("Repost", "reposts"),
        ("RSVP", "rsvps"),
        ("Drinking", "drinking"),
        ("Coffee", "drinking"),
    )

    for g in groups:
        lower_categories = [category.lower() for category in front_matter.metadata["categories"]]
        if g[0].lower() in lower_categories:
            site_config[g[1]] = site_config[g[1]] + [front_matter.metadata]
        elif g[1].rstrip("s") in directory_name:
            site_config[g[1]] = site_config[g[1]] + [front_matter.metadata]

    return site_config

def create_posts(pages_created_count, site_config):
    """
        Get all posts and execute process_page function to create them.
    """
    post_files = posts

    previous_page = None

    for post_item in range(0, len(post_files)):
        post_file = post_files[post_item]

        path = post_directory + "/" + post_file

        # do not copy dotfiles into site
        if post_file.startswith("."):
            continue

        if len(post_files) < post_item + 1:
            next_post_url = post_directory + "/" + post_files[post_item + 1]

            next_post = frontmatter.load(next_post_url)
        else:
            next_post_url = None
            next_post = None

        site_config = process_page(
            post_directory,
            path,
            site_config,
            "post",
            previous_page,
            next_post,
            next_post_url
        )

        previous_page = path

        pages_created_count += 1

    return site_config, pages_created_count

def render_series_fragment(site_config):
    """
        Adds "other posts in this series" fragment to series posts.
    """
    series_fragment = open("_includes/posts_in_series.html", "r").read()

    for post_object in site_config["series_posts"]:
        print("Generating 'Other posts in this series' fragment for " + post_object[1])
        category, post_name, page_url = post_object

        loader = jinja2.FileSystemLoader(searchpath="./")

        template = jinja2.Environment(loader=loader)

        rendered_series_text = template.from_string(series_fragment)

        posts_to_show = site_config["categories"].get(category)

        see_more_link = False

        if len(posts_to_show) > 10:
            see_more_link = True

        category_slug = category.replace(" ", "-").lower().replace("(", "").replace(")", "")

        rendered_series_text = rendered_series_text.render(
            posts_in_series=posts_to_show[:10],
            see_more_link=see_more_link,
            site=site_config,
            category_slug=category_slug,
            page={"url": page_url}
        )
        
        year_month_date = "/".join(post_name.split("-")[:3]) + "/"

        post_name = "-".join(post_name.split("-")[3:]).replace(".md", "").replace(".html", "")

        with open(OUTPUT + year_month_date + post_name + "/index.html", "r") as file:
            file_content = file.read()

        file_content = file_content.replace("<!--- posts_in_series -->", rendered_series_text)

        with open(OUTPUT + year_month_date + post_name + "/index.html", "w") as file:
            file.write(file_content)

    return series_fragment

def main():
    """
        Main function.
    """
    pages_created_count = 0

    site_config = yaml.load(open("config.yml", "r"), Loader=yaml.FullLoader)

    site_config["months"] = []
    site_config["years"] = []
    site_config["categories"] = {}
    site_config["series_posts"] = []

    if site_config.get("groups"):
        for group in site_config["groups"]:
            site_config[group] = []

    site_config, pages_created_count = create_posts(pages_created_count, site_config) 

    posts = site_config["posts"]

    # get all directories in folder
    all_directories = os.listdir(BASE_DIR)

    site_config["posts"].reverse()

    categories = site_config["categories"].keys()

    for category in categories:
        if category.lower() != "post":
            site_config["categories"][category].reverse()

    render_series_fragment(site_config)

    site_config, pages_created_count = create_non_post_files(all_directories, pages_created_count, site_config)

    os.mkdir("_site/category")

    if site_config.get("auto_generate"):
        if "category" in site_config["auto_generate"]:
            site_config, pages_created_count = create_archives.create_category_pages(
                site_config,
                BASE_DIR,
                OUTPUT,
                pages_created_count
            )

            # move _site/category/post to _site/posts/
            # this contains the main post archive (as defined as articles with the category "Post")
            os.rename("_site/category/post", "_site/posts")

        if "pagination" in site_config["auto_generate"]:
            site_config, pages_created_count = create_archives.create_pagination_pages(
                site_config,
                OUTPUT,
                pages_created_count
            )

        if "date_archive" in site_config["auto_generate"]:
            site_config, pages_created_count = create_archives.create_date_archive_pages(
                site_config,
                OUTPUT,
                pages_created_count,
                posts
            )

        if "list_page" in site_config["auto_generate"]:
            site_config, pages_created_count = create_archives.create_list_pages(
                BASE_DIR,
                site_config,
                OUTPUT,
                pages_created_count
            )

    create_archives.generate_sitemap(site_config, OUTPUT)

    feeds.create_feeds(site_config, posts)

    if os.path.exists("templates/robots.txt"):
        shutil.copyfile("templates/robots.txt", "_site/robots.txt")

    if os.path.exists("assets"):
        shutil.copytree("assets", "_site/assets")

    # remove config files from _site
    for file in os.listdir("_site"):
        if file.endswith((".pyc", ".cfg")):
            os.remove("_site/" + file)

    print("Pages generated: " + str(pages_created_count))

    per_second = str(pages_created_count / (datetime.datetime.now() - start_time).total_seconds())

    # round to 2 decimal places
    per_second = round(float(per_second), 2)

    print("Pages generated per second: " + str(per_second))

def slugify(post_path):
    """
        Remove special characters from a path name and prepare it for use.
    """
    return "".join([char for char in post_path.replace(" ", "-") if char.isalnum() or char in ALLOWED_SLUG_CHARS]).replace(".md", ".html")

if __name__ == "__main__":
    main()

    end_time = datetime.datetime.now()

    TIME_TAKEN = end_time - start_time

    print("Time taken to build website: " + str(TIME_TAKEN))