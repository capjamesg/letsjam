import concurrent.futures
# import cProfile
import datetime
import json
import os
import re
import shutil
import sys

import frontmatter
import jinja2
import markdown
import yaml
from bs4 import BeautifulSoup

import create_archives
import feeds
from config import ALLOWED_SLUG_CHARS, BASE_DIR, OUTPUT

start_time = datetime.datetime.now()

post_directory = "_posts"

# remove _site dir and all files in it
shutil.rmtree("_site", ignore_errors=True)

# create _site dir
if not os.path.exists("_site"):
    os.makedirs("_site")

if not os.path.exists("person_tags.json"):
    with open("person_tags.json", "w+") as f:
        f.write("{}")

posts = sorted(
    os.listdir("_posts"),
    key=lambda s: "".join([char for char in s if char.isnumeric()]),
)


def create_non_post_files(all_directories, pages_created_count, site_config):
    """
    Create all individual files (i.e. about.html) that aren't posts.
    """
    do_not_process = ("_posts", "_layouts", "_site", "assets", "_includes", "_drafts")

    # templates must be the last directory to process
    all_directories.remove("templates")

    all_directories.append("templates")

    for directory in all_directories:
        if directory == "templates":
            composite_stream = [
                post
                for post in site_config["notes"]
                if "Activity" not in post["categories"]
                and "Eat" not in post["categories"]
            ] + site_config["posts"]

            # order composite stream
            composite_stream.sort(key=lambda x: x["full_date"], reverse=True)

            site_config["stream"] = composite_stream

        directory_name = BASE_DIR + "/" + directory

        # don't process certain directories
        if (
            directory.startswith(do_not_process)
            or os.path.isfile(directory_name)
            or directory.startswith(".")
        ):
            continue

        all_files = os.listdir(directory_name)

        for file in sorted(
            all_files, key=lambda s: "".join([char for char in s if char.isnumeric()])
        ):
            f = directory_name + "/" + file

            if os.path.isdir(f):
                continue

            file_name = f.replace(directory_name, "")

            # do not copy dotfiles into site
            # also do not create archive.html file as that is created later

            if file_name.startswith("."):
                continue

            extension = file_name.split(".")[-1]

            # the archive page is created separately in the create_archive files
            if file_name == "/archive.html":
                continue

            # replies should allow person tagging
            # this feature only works if the generator can distinguish webmention pages from other pages
            # else, the generator will add a person tagging section to every page, which is not intended

            dir_name = directory_name.replace("./", "")

            if dir_name == "_replies":
                page_type = "webmention"
            else:
                page_type = None

            if extension in ("md", "html") and not os.path.isdir(f):
                process_page(directory_name, f, site_config, page_type=page_type)
            elif extension not in ("py", "pyc", "cfg") and not os.path.isdir(f):
                shutil.copy(f, OUTPUT + "/" + file_name)

            pages_created_count += 1

    return site_config, pages_created_count


def create_template(path, **kwargs):
    """
    Create a full page from a jinja2 template and its associated front matter.
    """

    if path.startswith("_layouts"):
        template_front_matter = frontmatter.loads(
            kwargs["site"]["layouts"][path.split("/")[-1]]
        )
    else:
        template_front_matter = frontmatter.load(path)

    loader = jinja2.FileSystemLoader(searchpath="./")

    template = jinja2.Environment(loader=loader)

    # register filter
    template.filters["long_date"] = create_archives.long_date
    template.filters["date_to_xml_string"] = create_archives.date_to_xml_string
    template.filters["archive_date"] = create_archives.archive_date

    # example markup for person tags
    # @jamesg.blog

    # example tag
    # {
    #     "jamesg.blog": {
    #         "full_name": "James' Coffee Blog",
    #         "url": "https://jamesg.blog"
    #     }
    # }

    if (
        "person_tags" in kwargs.keys()
        and "page_type" in kwargs.keys()
        and (kwargs["page_type"] == "post")
    ):

        person_tags = []

        for w in template_front_matter.content.split():
            w = w.lower()
            # don't get single @ characters that are alone
            if w.startswith("@") and w.strip() != "@":
                # ignore 's in the name
                w = w.split("'")[0]

                check_for_tag = kwargs["person_tags"].get(w.replace("@", ""), {})

                if check_for_tag == {}:
                    if "[" in w and "]" in w:
                        name = w.split("[")[-1].split("]")[0]
                    else:
                        name = w.replace("@", "")

                    template_front_matter.content = (
                        template_front_matter.content.replace(
                            w, f"[{name}](https://{w.replace('@', '')})"
                        )
                    )

                    person_tags.append(f"[{name}](https://{w.replace('@', '')})")
                elif "." in w:
                    # only run if . is in the tag, indicating a url

                    # replace @ mention with full name and anchor to url
                    template_front_matter.content = template_front_matter.content.replace(
                        w,
                        f"[{check_for_tag.get('full_name', w.replace('@', ''))}](https://{w.replace('@', '')})",
                    )

                    if check_for_tag.get("favicon"):
                        tag = "<p><a href='https://{}'><img src='{}' alt='{}' height='32' width='32' class='profile_tag'>  {}</a></p>".format(
                            check_for_tag.get("url", w),
                            check_for_tag.get("favicon", ""),
                            w.replace("@", ""),
                            check_for_tag.get("full_name", w.replace("@", "")),
                        )
                    else:
                        tag = f"[{check_for_tag.get('full_name', w.replace('@', ''))}]({check_for_tag.get('url')})"

                    person_tags.append(tag)

        person_tags = list(set(person_tags))

        if len(person_tags) > 0:
            template_front_matter.content = (
                template_front_matter.content
                + "\n\n## Mentioned in this post 👤\n\n"
                + "".join(person_tags)
            )

    if path.endswith(".md"):
        template_front_matter.content = markdown.markdown(template_front_matter.content)

    # don't look for person tags in higher-level html files (i.e. main templates)
    if "page_type" in kwargs.keys():
        del kwargs["page_type"]

    new_template = template.from_string(template_front_matter.content)

    if (
        len(sys.argv) > 1
        and sys.argv[1] == "--retro"
        and template_front_matter.metadata.get("layout")
        and template_front_matter.metadata["layout"] == "default"
    ):
        template_front_matter.metadata["layout"] = "retro"

    if template_front_matter.metadata.get("layout"):
        if type(kwargs["site"]) == dict:
            parent_front_matter = frontmatter.loads(
                kwargs["site"]["layouts"][
                    template_front_matter.metadata["layout"] + ".html"
                ]
            )
        else:
            parent_front_matter = frontmatter.load(
                "_layouts/" + template_front_matter.metadata["layout"] + ".html"
            )

        parent_template = template.from_string(parent_front_matter.content)

        if (
            len(sys.argv) > 1
            and sys.argv[1] == "--retro"
            and parent_front_matter.metadata.get("layout")
            and parent_front_matter.metadata["layout"] == "default"
        ):
            parent_front_matter.metadata["layout"] = "retro"

        new_template = parent_template.render(
            content=new_template.render(kwargs), **kwargs
        )

        kwargs["content"] = new_template

        if parent_front_matter.metadata.get("layout"):
            template = create_template(
                "_layouts/" + parent_front_matter.metadata["layout"] + ".html", **kwargs
            )
        else:
            template = new_template
    else:
        template = new_template.render(kwargs)

    if len(sys.argv) > 1 and sys.argv[1] == "--retro":
        template = template.replace(
            '<div id="main">', '<div id="main" class="flex_right_home">'
        )

    # soup = BeautifulSoup(template, "html.parser")

    # all links
    # all_links = soup.find_all("a")

    # with open("all_links.json", "a+") as f:
    #     for link in all_links:
    #         if link.get("href") and "//" in link.get("href") and "jamesg.blog" not in link.get("href") and not link.get("href").startswith("/"):
    #             classes = link.get("class")
    #             f.write(json.dumps({"dst": link.get("href"), "src": "https://jamesg.blog", "classes": classes}) + "\n")

    return template


def process_page(
    directory_name,
    file_name,
    site_config,
    page_type=None,
    previous_page=None,
    next_post=None,
    next_post_url=None,
    person_tags={},
):

    front_matter = frontmatter.load(file_name)

    if previous_page:
        front_matter.metadata["previous"] = {
            "title": previous_page.metadata["title"],
            "url": previous_page.metadata["url"],
        }

    else:
        front_matter.metadata["previous"] = {"title": "", "url": ""}

    if next_post is not None:
        front_matter.metadata["next"] = {
            "title": next_post["title"],
            "url": next_post_url,
        }
    else:
        front_matter.metadata["next"] = {"title": "", "url": ""}

    if front_matter.metadata == {}:
        return site_config

    # do not process pages with no content
    if len(front_matter.content) == 0:
        return site_config

    front_matter.metadata["photo_grid"] = "false"
    front_matter.metadata["all_images"] = []

    if front_matter.metadata.get("categories") is None:
        front_matter.metadata["categories"] = []

    if type(front_matter.metadata["categories"]) == str:
        front_matter.metadata["categories"] = [
            front_matter.metadata["categories"]
        ] + front_matter.metadata.get("category", [])
    else:
        front_matter.metadata["categories"] = front_matter.metadata[
            "categories"
        ] + front_matter.metadata.get("category", [])

    if front_matter.metadata.get("ate"):
        front_matter.metadata["categories"] = front_matter.metadata["categories"] + [
            "Eat"
        ]

    if file_name.endswith(".md"):
        front_matter.content = markdown.markdown(front_matter.content)

    soup = BeautifulSoup(front_matter.content, "lxml")

    as_text = soup.get_text()

    images = soup.find_all("img")

    if images:
        front_matter.metadata["image"] = [images[0].get("src", "")]

        front_matter.metadata["all_images"] = images

    # first paragraph sentences will be considered "excerpt" value

    # .replace(" @", "") removes @ mentions
    # @ mentions are not parsed at this time so they should not be formatted as raw @ mentions in the excerpts

    front_matter.metadata["excerpt"] = " ".join(
        [str(sentence) for sentence in soup.find_all("p")[:1]]
    ).replace(" @", "")

    # use first sentence for meta description
    front_matter.metadata["meta_description"] = (
        "".join(front_matter.metadata["excerpt"].split(". ")[0]).replace(" @", "")
        + "..."
    )
    front_matter.metadata["description"] = " ".join(
        [sentence.text for sentence in soup.find_all("p")[:1]]
    ).replace(" @", "")

    layout_types = ["like", "bookmark", "repost", "webmention", "note", "watche"]

    if front_matter.metadata["layout"].rstrip("s").lower() in layout_types:
        site_config[front_matter.metadata["layout"].rstrip("s")] = site_config[
            front_matter.metadata["layout"].rstrip("s")
        ] + [front_matter.metadata]

    print("Generating " + file_name)

    if (
        not front_matter.metadata.get("title")
        and len(front_matter.get("categories", [])) > 0
    ):
        title = front_matter.metadata["categories"][-1]

        front_matter.metadata["title"] = title.replace("-", " ").title()
    elif not front_matter.metadata.get("title"):
        front_matter.metadata["title"] = "Post by James"

    if type(front_matter.metadata.get("categories", [])) == list:
        front_matter.metadata["categories"] = front_matter.metadata.get(
            "categories", []
        ) + front_matter.metadata.get("category", [])

    if "note" in front_matter.metadata["categories"]:
        hashtags = re.findall(r"#(\w+)", as_text)

        for h in hashtags:
            front_matter.content = front_matter.content.replace(
                "#" + h, "<a href='/tag/" + h.lower() + "' rel='tag'>#" + h + "</a>"
            )

        hashtags = [tag.lower() for tag in hashtags]

        if len(hashtags) > 0:
            front_matter.metadata["tags"] = (
                front_matter.metadata.get("tags", []) + hashtags
            )

        for tag in front_matter.metadata.get("tags", []):
            if site_config["tags"].get(tag) is None:
                site_config["tags"][tag] = [front_matter.metadata]
            else:
                site_config["tags"][tag] = site_config["tags"][tag] + [
                    front_matter.metadata
                ]

    if page_type == "post" or "note" in front_matter.metadata["categories"]:
        path_to_save = OUTPUT + "/" + file_name.replace(BASE_DIR, "").strip("/")

        file = file_name.split("/")[-1]

        year = file.split("-")[0]
        month = file.split("-")[1]
        day = file.split("-")[2]

        # if post published after today, do not generate it
        # this ensures content scheduled for the future is not published
        if (
            datetime.datetime.strptime(year + "-" + month + "-" + day, "%Y-%m-%d")
            > datetime.datetime.now()
        ):
            return site_config

        site_config["years"].append(year)
        site_config["months"].append(month)

        front_matter.metadata["date"] = datetime.datetime.strptime(
            year + "-" + month + "-" + day, "%Y-%m-%d"
        )

        # if more than two image in a post, create grid
        if len(images) > 2:
            front_matter.metadata["photo_grid"] = "true"

            # delete all images from main body

            for image in images:
                front_matter.content = front_matter.content.replace(str(image), "")

            front_matter.metadata["content"] = front_matter.content

        if page_type == "post":
            if not os.path.exists(OUTPUT + "/" + year + "/" + month + "/" + day):
                os.makedirs(OUTPUT + "/" + year + "/" + month + "/" + day)

            path_to_save = (
                OUTPUT
                + "/"
                + year
                + "/"
                + month
                + "/"
                + day
                + "/"
                + "-".join(file.split("-")[3:]).split(".")[0]
                + "/index.html"
            )
        else:
            path_to_save = (
                OUTPUT
                + "/"
                + file_name.strip("/")
                .replace("templates/", "")
                .replace("_", "")
                .replace(".md", "")
                + "/index.html"
            )
    else:
        path_to_save = (
            OUTPUT
            + "/"
            + file_name.strip("/")
            .replace("templates/", "")
            .replace("_", "")
            .replace(".md", "")
            + "/index.html"
        )

        if path_to_save.endswith("html") and not path_to_save.endswith(".html"):
            path_to_save = path_to_save.replace("html", ".html")

    if front_matter.get("permalink") and front_matter.get("permalink").endswith(
        ".html"
    ):
        path_to_save = OUTPUT + front_matter.get("permalink").rstrip("/")
    elif front_matter.get("permalink"):
        path_to_save = (
            OUTPUT + front_matter.get("permalink").rstrip("/") + "/" + "index.html"
        )

    url = (
        path_to_save.replace(OUTPUT, "")
        .replace("/index.html", "/")
        .replace("/templates/", "")
        .replace("index.html", "/")
        .replace(".html", "")
        .replace("./", "")
    )

    front_matter.metadata["url"] = url
    front_matter.metadata["slug"] = url

    if "Post" in front_matter.metadata["categories"]:
        post_type = "article"
    else:
        post_type = "post"

    published_date = feeds.get_published_date(
        file_name.split("/")[-1],
        post_type=post_type,
        published=front_matter.metadata.get("published", ""),
    )

    if published_date == "" and front_matter.metadata.get("published"):
        if isinstance(front_matter.metadata["published"], datetime.datetime):
            front_matter.metadata["full_date"] = front_matter.metadata[
                "published"
            ].strftime("%Y-%m-%d %H:%M:%S-00:00")
            front_matter.metadata["published"] = front_matter.metadata[
                "published"
            ].strftime("%B %d, %Y")
        else:
            front_matter.metadata["full_date"] = datetime.datetime.strptime(
                front_matter.metadata["published"], "%Y-%m-%dT%H:%M:%S.%f"
            ).strftime("%Y-%m-%d %H:%M:%S-00:00")
            front_matter.metadata["published"] = datetime.datetime.strptime(
                front_matter.metadata["published"], "%Y-%m-%dT%H:%M:%S.%f"
            ).strftime("%B %d, %Y")

    else:
        if isinstance(published_date, datetime.datetime):
            front_matter.metadata["published"] = published_date.strftime("%B %d, %Y")
            front_matter.metadata["full_date"] = published_date.strftime(
                "%Y-%m-%d %H:%M:%S-00:00"
            )
        elif not front_matter.metadata.get("published"):
            front_matter.metadata["published"] = ""
            front_matter.metadata["full_date"] = ""

    front_matter.metadata["content"] = front_matter.content

    front_matter.metadata["created_on"] = datetime.datetime.fromtimestamp(
        os.stat(file_name).st_ctime
    ).strftime("%B %d, %Y")
    front_matter.metadata["modified_on"] = datetime.datetime.fromtimestamp(
        os.stat(file_name).st_mtime
    ).strftime("%B %d, %Y")

    rendered_string = create_template(
        file_name,
        site=site_config,
        page=front_matter.metadata,
        paginator=None,
        person_tags=person_tags,
        page_type=page_type,
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

    if page_type == "post" or "note" in front_matter.metadata["categories"]:
        site_config["posts"] = site_config["posts"] + [front_matter.metadata]

        if type(front_matter.metadata["categories"]) == str:
            front_matter.metadata["categories"] = [front_matter.metadata["categories"]]

        for category in front_matter.metadata["categories"]:
            if "(Series)" in category:
                site_config["series_posts"].append(
                    [
                        front_matter.metadata["categories"][0],
                        file_name.replace("_posts", ""),
                        front_matter.metadata["url"],
                    ]
                )

            if (
                "<img" in front_matter.content
                and "note" in front_matter.metadata["categories"]
            ):
                site_config["notes_with_images"] = site_config["notes_with_images"] + [
                    front_matter.metadata["url"]
                ]

            if site_config["categories"].get(category) is None:
                site_config["categories"][category] = [front_matter.metadata]
            else:
                site_config["categories"][category] = site_config["categories"][
                    category
                ] + [front_matter.metadata]

    groups = (
        ("Like", "likes"),
        ("Bookmark", "bookmarks"),
        ("Reply", "replies"),
        ("Repost", "reposts"),
        ("Watch", "watches"),
        ("Note", "notes"),
    )

    for g in groups:
        lower_categories = [
            category.lower() for category in front_matter.metadata["categories"]
        ]
        if g[0].lower() in lower_categories:
            site_config[g[1]] = site_config[g[1]] + [front_matter.metadata]
        elif g[1].rstrip("s") in directory_name:
            site_config[g[1]] = site_config[g[1]] + [front_matter.metadata]

    return site_config, front_matter


def create_posts(pages_created_count, site_config):
    """
    Get all posts and execute process_page function to create them.
    """
    post_files = posts

    previous_page = None

    with open("person_tags.json", "r") as f:
        person_tags = json.load(f)

    tasks = []

    with concurrent.futures.ThreadPoolExecutor(max_workers=15) as executor:
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

            tasks.append(
                executor.submit(
                    process_page,
                    post_directory,
                    path,
                    site_config,
                    "post",
                    previous_page,
                    next_post,
                    next_post_url,
                    person_tags,
                )
            )

            previous_page = ""

            pages_created_count += 1

    for _ in concurrent.futures.as_completed(tasks):
        try:
            pages_created_count += 1
            print("s")
        except Exception as exc:
            print(exc)

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

        category_slug = (
            category.replace(" ", "-").lower().replace("(", "").replace(")", "")
        )

        rendered_series_text = rendered_series_text.render(
            posts_in_series=posts_to_show[:10],
            see_more_link=see_more_link,
            site=site_config,
            category_slug=category_slug,
            page={"url": page_url},
        )

        year_month_date = "/".join(post_name.split("-")[:3]) + "/"

        post_name = (
            "-".join(post_name.split("-")[3:]).replace(".md", "").replace(".html", "")
        )

        with open(OUTPUT + year_month_date + post_name + "/index.html", "r") as file:
            file_content = file.read()

        file_content = file_content.replace(
            "<!--- posts_in_series -->", rendered_series_text
        )

        with open(OUTPUT + year_month_date + post_name + "/index.html", "w") as file:
            file.write(file_content)

    return series_fragment


def main():
    """
    Main function.
    """
    pages_created_count = 0

    site_config = yaml.load(open("config.yml", "r"), Loader=yaml.FullLoader)

    site_config["pages"] = []
    site_config["notes_with_images"] = []

    site_config["months"] = []
    site_config["years"] = []

    site_config["categories"] = {}
    site_config["tags"] = {}

    site_config["series_posts"] = []
    site_config["layouts"] = {}

    if site_config.get("groups"):
        for group in site_config["groups"]:
            site_config[group] = []

    # open all layouts files and save them to memory
    layouts = os.listdir("_layouts")

    for l in layouts:
        with open("_layouts/" + l, "r") as file:
            site_config["layouts"][l] = file.read()

    site_config, pages_created_count = create_posts(pages_created_count, site_config)

    posts = site_config["posts"]

    # get all directories in base folder
    all_directories = os.listdir(BASE_DIR)

    site_config["posts"].reverse()

    categories = site_config["categories"].keys()

    site_config["notes"] = [n for n in site_config["notes"] if "Activity" not in n]

    for category in categories:
        # order by date published in descending order
        site_config["categories"][category].sort(
            key=lambda x: x["full_date"], reverse=True
        )

    render_series_fragment(site_config)

    site_config, pages_created_count = create_non_post_files(
        all_directories, pages_created_count, site_config
    )

    os.mkdir("_site/category")

    if site_config.get("auto_generate"):
        if "category" in site_config["auto_generate"]:
            site_config, pages_created_count = create_archives.create_category_pages(
                site_config, OUTPUT, pages_created_count, page_type="category"
            )

            site_config, pages_created_count = create_archives.create_category_pages(
                site_config, OUTPUT, pages_created_count, page_type="tag"
            )

        if "pagination" in site_config["auto_generate"]:
            with concurrent.futures.ThreadPoolExecutor(max_workers=15) as executor:
                futures = []

                for category, entries in site_config["categories"].items():
                    futures.append(
                        executor.submit(
                            create_archives.create_category_pages,
                            site_config,
                            OUTPUT,
                            pages_created_count,
                            entries,
                            category,
                        )
                    )

                for _ in concurrent.futures.as_completed(futures):
                    try:
                        pages_created_count += 1
                    except Exception as exc:
                        print(exc)

        if "date_archive" in site_config["auto_generate"]:
            (
                site_config,
                pages_created_count,
            ) = create_archives.create_date_archive_pages(
                site_config, OUTPUT, pages_created_count, posts
            )

        if "list_page" in site_config["auto_generate"]:
            site_config, pages_created_count = create_archives.create_list_pages(
                BASE_DIR, site_config, OUTPUT, pages_created_count
            )

    create_archives.generate_sitemap(site_config, OUTPUT)

    feeds.create_feeds(site_config, posts)

    if os.path.exists("templates/robots.txt"):
        shutil.copyfile("templates/robots.txt", "_site/robots.txt")

    if os.path.exists("assets"):
        shutil.copytree("assets", "_site/assets")

    # remove config files from _site
    for file in os.listdir("_site"):
        if file.endswith((".pyc", ".cfg", ".log")) or file.startswith("."):
            os.remove("_site/" + file)

    # generate sparklines

    collections_to_build_sparklines_for = ["posts", "likes", "notes", "bookmarks"]

    sparklines = ""

    for c in collections_to_build_sparklines_for:
        dates = {}

        for i in range(0, 90):
            dates[
                (datetime.datetime.now() - datetime.timedelta(days=i)).strftime(
                    "%Y-%m-%d"
                )
            ] = 0

        for post in site_config[c]:
            if c == "posts":
                date = post["date"].strftime("%Y-%m-%d")
            else:
                date = datetime.datetime.strptime(
                    post["full_date"], "%Y-%m-%d %H:%M:%S-00:00"
                ).strftime("%Y-%m-%d")

            if dates.get(date) is not None:
                dates[date] += 1

        values = dates.values()

        # convert values to list
        data_points = list(values)

        data_points.reverse()

        number_of_posts = len(site_config[c])

        if c == "posts":
            url = "/category/post/"
        else:
            url = f"/{c}/"

        sparklines += f"""
        <p><a href="{url}">{number_of_posts} {c.title()}</a> <embed class="light_mode" src="/assets/sparkline.svg?{','.join([str(val) for val in data_points])}"
        class="sparkline" width=100 height=15 /><embed class="dark_mode" src="/assets/sparkline_dark_mode.svg?{','.join([str(val) for val in data_points])}"
        class="sparkline" width=100 height=15 /></p>"""

    with open("_site/index.html", "r") as file:
        file_content = file.read()

    file_content = file_content.replace("<!--- sparkline -->", sparklines)

    with open("_site/index.html", "w") as file:
        file.write(file_content)

    # move all rsvps to their own permalink
    shutil.move("_site/category/rsvp/", "_site/rsvp/")

    print("Pages generated: " + str(pages_created_count))

    per_second = str(
        pages_created_count / (datetime.datetime.now() - start_time).total_seconds()
    )

    # round to 2 decimal places
    per_second = round(float(per_second), 2)

    print("Pages generated per second: " + str(per_second))


def slugify(post_path):
    """
    Remove special characters from a path name and prepare it for use.
    """
    return "".join(
        [
            char
            for char in post_path.replace(" ", "-")
            if char.isalnum() or char in ALLOWED_SLUG_CHARS
        ]
    ).replace(".md", ".html")


if __name__ == "__main__":
    # cProfile.run("main()", filename="profile.txt")
    main()

    end_time = datetime.datetime.now()

    TIME_TAKEN = end_time - start_time

    print("Time taken to build website: " + str(TIME_TAKEN))
