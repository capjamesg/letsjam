import concurrent.futures
import datetime
import json
import os
import shutil

import frontmatter
import jinja2
import markdown
import requests
import yaml
from bs4 import BeautifulSoup

import create_archives
import to_kml

BASE_DIR = "."
OUTPUT = "_site"
ALLOWED_SLUG_CHARS = ["-", "/", ".", "_"]

start_time = datetime.datetime.now()

post_directory = "_posts"


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
            composite_stream = site_config["posts"]

            # order composite stream
            composite_stream.sort(key=lambda x: x["full_date"], reverse=True)

            # ignore all pages with hidden: true
            composite_stream = [
                x for x in composite_stream if x.get("hidden", "") != "true"
            ]

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

        # if poll, list all recursive too
        if directory == "_poll":
            all_files = []

            files = os.listdir(directory_name)

            for f in files:
                if os.path.isdir(directory_name + "/" + f):
                    for file in os.listdir(directory_name + "/" + f):
                        all_files.append(f + "/" + file + "/index.md")

        categories = [site for site in site_config["categories"].keys()]

        # order alphabetically, ignore case
        categories = sorted(categories, key=lambda s: s.lower())

        all_categories = []

        for c in categories:
            all_categories.append(
                {"name": c, "post_count": len(site_config["categories"][c])}
            )

        tags = [site for site in site_config["tags"].keys()]

        # order alphabetically
        tags = sorted(tags, key=lambda s: s.lower())

        all_tags = []

        for c in tags:
            all_tags.append({"name": c, "post_count": len(site_config["tags"][c])})

        for file in sorted(
            all_files, key=lambda s: "".join([char for char in s if char.isnumeric()])
        ):
            f = directory_name + "/" + file

            file_name = f.replace(directory_name, "")

            if (
                os.path.isdir(f)
                or file_name.startswith(".")
                or file_name == "/archive.html"
            ):
                continue

            extension = file_name.split(".")[-1]

            dir_name = directory_name.replace("./", "")

            if dir_name == "_replies":
                page_type = "webmention"
            else:
                page_type = None

            if extension in ("md", "html") and not os.path.isdir(f):
                process_page(
                    f,
                    site_config,
                    page_type=page_type,
                    categories=all_categories,
                    tags=all_tags,
                )
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
    template.filters["list_archive_date"] = create_archives.list_archive_date

    if path.endswith(".md"):
        template_front_matter.content = markdown.markdown(template_front_matter.content)

    new_template = template.from_string(template_front_matter.content)

    kwargs.get("page", {})["today"] = str(datetime.datetime.now().strftime("%Y%m%d"))

    if kwargs.get("end_date"):
        kwargs["page"]["end_date_formatted"] = kwargs["end_date"].strftime("%Y-%m-%d")

    if template_front_matter.metadata.get("layout"):
        if type(kwargs["site"]) == dict:
            parent_front_matter = frontmatter.loads(
                kwargs["site"]["layouts"][
                    template_front_matter.metadata["layout"] + ".html"
                ]
            )
        else:
            parent_front_matter = frontmatter.loads(
                "_layouts/" + template_front_matter.metadata["layout"] + ".html"
            )

        parent_template = template.from_string(parent_front_matter.content)

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

    return template


def process_page(
    file_name,
    site_config,
    page_type=None,
    previous_page=None,
    next_post=None,
    next_post_url=None,
    person_tags={},
    categories=[],
    tags=[],
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

    front_matter.metadata["categories"] = front_matter.metadata.get("categories", [])

    if type(front_matter.metadata["categories"]) == str:
        front_matter.metadata["categories"] = [
            front_matter.metadata["categories"]
        ] + front_matter.metadata.get("category", [])
    else:
        front_matter.metadata["categories"] = front_matter.metadata[
            "categories"
        ] + front_matter.metadata.get("category", [])

    if file_name.endswith(".md"):
        front_matter.content = markdown.markdown(front_matter.content)

    soup = BeautifulSoup(front_matter.content, "lxml")

    images = soup.find_all("img")

    # first paragraph sentences will be considered "excerpt" value

    # .replace(" @", "") removes @ mentions
    # @ mentions are not parsed at this time so they should not be formatted as raw @ mentions in the excerpts

    front_matter.metadata["excerpt"] = " ".join(
        [str(sentence) for sentence in soup.find_all("p")[:1]]
    ).replace(" @", "")

    # use first sentence for meta description
    if front_matter.metadata.get("meta_description") is None:
        front_matter.metadata["meta_description"] = (
            "".join(front_matter.metadata["excerpt"].split(". ")[0]).replace(" @", "")
            + "..."
        )

    if front_matter.metadata.get("description") is None:
        front_matter.metadata["description"] = " ".join(
            [sentence.text for sentence in soup.find_all("p")[:1]]
        ).replace(" @", "")

    if not front_matter.metadata.get("layout"):
        return

    if site_config.get(front_matter.metadata["layout"]) is not None:
        site_config[front_matter.metadata["layout"]] = site_config[
            front_matter.metadata["layout"]
        ] + [front_matter.metadata]

    print("Generating " + file_name)

    if (
        not front_matter.metadata.get("title")
        and len(front_matter.get("categories", [])) > 0
    ):
        title = front_matter.metadata["categories"][-1]

        front_matter.metadata["title"] = title.replace("-", " ").title()

    if type(front_matter.metadata.get("categories", [])) == list:
        front_matter.metadata["categories"] = front_matter.metadata.get(
            "categories", []
        ) + front_matter.metadata.get("category", [])

    if (
        page_type == "post"
        or "note" in front_matter.metadata["categories"]
        or page_type == "poll"
    ):
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

        if page_type == "post":
            dir_name = OUTPUT + "/" + year + "/" + month + "/" + day
            if not os.path.exists(dir_name):
                os.makedirs(dir_name)

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

    published_date = get_published_date(
        file_name.split("/")[-1],
        post_type=post_type,
        published=front_matter.metadata.get("published", ""),
    )

    if published_date == "" and front_matter.metadata.get("published"):
        if isinstance(front_matter.metadata["published"], datetime.datetime):
            date_object = front_matter.metadata["published"]
        else:
            date_object = datetime.datetime.strptime(
                front_matter.metadata["published"], "%Y-%m-%dT%H:%M:%S.%f"
            )

        front_matter.metadata["full_date"] = date_object.strftime(
            "%Y-%m-%d %H:%M:%S-00:00"
        )
        front_matter.metadata["published"] = date_object.strftime("%B %d, %Y")
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

    page_tags = [
        "<a href='/tag/" + tag.lower().replace(" ", "-") + "/'>" + tag + "</a>, "
        for tag in front_matter.metadata.get("tags", [])
    ]

    # get rid of last ,
    if len(page_tags) > 0:
        page_tags[-1] = page_tags[-1].replace("</a>, ", "</a>")

    front_matter.metadata["page_tags"] = "".join(page_tags)

    rendered_string = create_template(
        file_name,
        site=site_config,
        page=front_matter.metadata,
        paginator=None,
        person_tags=person_tags,
        page_type=page_type,
        categories=categories,
        tags=tags,
    )

    if post_type == "article" and front_matter.metadata.get("hidden") != "true":
        for image in images:
            site_config["photos"] = site_config["photos"] + [
                {
                    "alt": image["alt"],
                    "src": image["src"],
                    "page_url": url,
                    "published": front_matter.metadata["full_date"],
                }
            ]

    dir_to_save = "/".join(path_to_save.split("/")[:-1])

    if not os.path.exists(dir_to_save):
        os.makedirs(dir_to_save)

    with open(path_to_save, "w+") as file:
        file.write(rendered_string)

    site_config["pages"] +=  [front_matter.metadata["url"]]

    if page_type == "post" or "note" in front_matter.metadata["categories"]:
        site_config["posts"] += [front_matter.metadata]

        for category in front_matter.metadata["categories"]:
            if "(Series)" in category:
                site_config["series_posts"].append(
                    [
                        front_matter.metadata["categories"][0],
                        file_name.replace("_posts", ""),
                        front_matter.metadata["url"],
                    ]
                )
            
            site_config["categories"][category] = site_config["categories"].get(category, [])  + [front_matter.metadata]

    for tag in front_matter.metadata.get("tags", []):
        site_config["tags"][tag] = site_config["tags"].get(tag.lower(), []) + [
            front_matter.metadata
        ]

    for c in front_matter.metadata["categories"]:
        site_config[c.lower()] = site_config.get(c.lower(), []) + [front_matter.metadata]

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
        except Exception as exc:
            raise exc

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

    cafes = to_kml.transform_cafes_to_string_kml_file()

    all_cafes_excluding_world_travel = []
    all_cities = []

    for location, values in cafes.items():
        if "World" not in location:
            for v in values:
                all_cafes_excluding_world_travel.append(v)
        else:
            all_cities.append(values)

    site_config["cafes"] = cafes
    cafe_list = list(cafes.keys())

    site_config["cafes"]["GlobalAll"] = all_cities

    # "World2021" and "World2022" are reserved for my /travel/ maps
    cafe_list.remove("World2021")
    cafe_list.remove("World2022")
    cafe_list.remove("RomeChurches")

    new_items = {
        "cafe_list": cafe_list,
        "all_cafes_excluding_world_travel": all_cafes_excluding_world_travel,
        "pages": [],
        "notes_with_images": [],
        "months": [],
        "years": [],
        "categories": {},
        "tags": {},
        "series_posts": [],
        "layouts": {},
        "photos": [],
        "checkin": [],
    }

    site_config = {**site_config, **new_items}

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

    # sort photos by published
    sorted(site_config["photos"], key=lambda k: k["published"])
    # get all directories in base folder
    all_directories = os.listdir(BASE_DIR)

    site_config["posts"].reverse()

    categories = site_config["categories"].keys()

    for category in categories:
        # order by date published in descending order
        site_config["categories"][category].sort(
            key=lambda x: x["full_date"], reverse=True
        )

    render_series_fragment(site_config)

    site_config, pages_created_count = create_non_post_files(
        all_directories, pages_created_count, site_config
    )

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
                        raise exc

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

    if os.path.exists("templates/robots.txt"):
        shutil.copyfile("templates/robots.txt", "_site/robots.txt")

    if os.path.exists("assets"):
        shutil.copytree("assets", "_site/assets")

    # remove config files from _site
    for file in os.listdir("_site"):
        if file.endswith((".pyc", ".cfg", ".log")) or file.startswith("."):
            os.remove("_site/" + file)

    # generate sparklines

    collections_to_build_sparklines_for = ["posts"]

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

        get_wiki_sparkline = requests.get(
            "https://sparkline.jamesg.blog/?username=Jamesg.blog&api_url=https://indieweb.org/wiki/api.php&only_image=true&days=30"
        )

        if get_wiki_sparkline.status_code == 200:
            wiki_sparkline_url = get_wiki_sparkline.history[-1].url
        else:
            wiki_sparkline_url = ""

        sparklines += f"""
        <p><a href="{url}">{number_of_posts} {c.title()}</a> <embed class="light_mode" src="/assets/sparkline.svg?{','.join([str(val) for val in data_points])}"
        class="sparkline" width=100 height=15 /></p>
        <p><a href="https://indieweb.org/User:Jamesg.blog">IndieWeb Wiki Contributions</a> <embed class="light_mode" src="{wiki_sparkline_url}"
        class="sparkline" width=100 height=15 /></p>"""

        # dark mode sparkline for reference
        # <embed class="dark_mode" src="/assets/sparkline_dark_mode.svg?{','.join([str(val) for val in data_points])}" class="sparkline" width=100 height=15 />

    with open("_site/index.html", "r") as file:
        file_content = file.read()

    file_content = file_content.replace("<!--- sparkline -->", sparklines)

    with open("_site/index.html", "w") as file:
        file.write(file_content)

    print("Pages generated: " + str(pages_created_count))

    per_second = str(
        pages_created_count / (datetime.datetime.now() - start_time).total_seconds()
    )

    # round to 2 decimal places
    per_second = round(float(per_second), 2)

    print("Pages generated per second: " + str(per_second))


if __name__ == "__main__":
    main()

    end_time = datetime.datetime.now()

    TIME_TAKEN = end_time - start_time

    print("Time taken to build website: " + str(TIME_TAKEN))
