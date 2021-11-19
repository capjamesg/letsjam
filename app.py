import create_archives
import feeds
from config import BASE_DIR, OUTPUT, ALLOWED_SLUG_CHARS
import config
import frontmatter
import datetime
import markdown
import jinja2
import shutil
import os

start_time = datetime.datetime.now()

post_directory = "/home/james/Projects/letsjam/_posts"

# remove _site dir and all files in it
shutil.rmtree("_site", ignore_errors=True)

# create _site dir
if not os.path.exists("_site"):
    os.makedirs("_site")

posts = sorted(os.listdir("_posts"), key=lambda s: "".join([char for char in s if char.isnumeric()]))

def create_non_post_files(all_directories, is_retro, pages_created_count, site_config):
    do_not_process = ("_posts", "_layouts", "_site", "assets", "_includes")

    for directory in all_directories:
        directory_name = BASE_DIR + "/" + directory

        # don't process certain directories
        if directory.startswith(do_not_process) or os.path.isfile(directory_name) or directory.startswith("."):
            continue

        all_files = os.listdir(directory_name)

        for file in all_files:
            f = directory_name + "/" + file

            file_name = f.replace(directory_name, "")

            extension = file_name.split(".")[-1]

            # do not copy dotfiles into site
            if file_name.startswith("."):
                continue

            if extension == "md" or extension == "html":
                site_config = process_page(directory_name, f, site_config, None, None, is_retro)
            else:
                shutil.copy(f, OUTPUT + "/" + file_name)

            pages_created_count += 1

    return site_config, pages_created_count

def create_template(path, **kwargs):
    template_front_matter = frontmatter.load(path)

    loader = jinja2.FileSystemLoader(searchpath="./")

    template = jinja2.Environment(loader=loader)

    # register filter
    template.filters["long_date"] = create_archives.long_date
    template.filters["date_to_xml_string"] = create_archives.date_to_xml_string

    new_template = template.from_string(template_front_matter.content)

    if template_front_matter.metadata.get("layout"):
        parent_front_matter = frontmatter.load("_layouts/" + template_front_matter.metadata["layout"] + ".html")
        parent_template = template.from_string(parent_front_matter.content)

        kwargs["content"] = new_template.render(**kwargs)

        template = parent_template.render(kwargs)

        if parent_front_matter.metadata.get("layout"):
            parent_template = create_template("_layouts/" + parent_front_matter.metadata["layout"] + ".html", **kwargs)
    else:
        template = new_template.render(kwargs)
    
    return template

def process_page(directory_name, file_name, site_config, page_type=None, previous_page=None, is_retro=False, next_post=None, next_post_url=None):
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

    if next_post != None:
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
        return

    if front_matter.metadata.get("categories") == None:
        front_matter.metadata["categories"] = []

    groups = (
        ("Like", "likes"),
        ("Bookmark", "bookmarks"),
        ("Webmention", "replies"),
        ("Reply", "replies"),
        ("Repost", "reposts"),
        ("RSVP", "rsvps"),
        ("Drinking", "coffee"),
    )

    for g in groups:
        if g[0] in front_matter.metadata["categories"]:
            site_config[g[1]] = site_config[g[1]] + [front_matter.metadata]

    if file_name.endswith(".md"):
        front_matter.content = markdown.markdown(front_matter.content)

    # first three sentences will be considered "excerpt" value
    front_matter.metadata["excerpt"] = ". ".join(front_matter.content.split(". ")[:3])
    front_matter.metadata["slug"] = slugify(file_name.replace(".html", ""))
    front_matter.metadata["url"] = front_matter.metadata["slug"]

    if front_matter.metadata["layout"].rstrip("s") in ["like", "bookmark", "repost", "webmention", "note"]:
        site_config[front_matter.metadata["layout"].rstrip("s")] = site_config[front_matter.metadata["layout"].rstrip("s")] + [front_matter.metadata]

    print("Generating " + file_name)

    rendered_string = create_template(file_name, site=site_config, page=front_matter.metadata, paginator=None)

    if page_type == "post":
        path_to_save = OUTPUT + "/" + file_name.replace(BASE_DIR, "").strip("/")

        file = file_name.split("/")[-1]

        year = file.split("-")[0]
        month = file.split("-")[1]
        day = file.split("-")[2]

        site_config["years"].append(year)
        site_config["months"].append(month)

        front_matter.metadata["date"] = datetime.datetime.strptime(year + "-" + month + "-" + day, "%Y-%m-%d")

        if not os.path.exists(OUTPUT + "/" + year + "/" + month + "/" + day):
            os.makedirs(OUTPUT + "/" + year + "/" + month + "/" + day)
        
        path_to_save = OUTPUT + "/" + year + "/" + month + "/" + day + "/" + "-".join(file.split("-")[3:]).split(".")[0] + ".html"
    else:
        path_to_save = OUTPUT + "/" + file_name.replace(BASE_DIR, "").strip("/").replace("templates/", "").replace("_", "")
        
    front_matter.metadata["url"] = path_to_save.replace(OUTPUT, "")

    dir_to_save = "/".join(path_to_save.split("/")[:-1])

    if not os.path.exists(dir_to_save):
        os.makedirs(dir_to_save)

    with open(path_to_save, "w+") as file:
        file.write(rendered_string)

    site_config["pages"] = site_config["pages"] + [front_matter.metadata["url"]]

    if page_type == "post":
        site_config["posts"] = site_config["posts"] + [front_matter.metadata]

        for category in front_matter.metadata["categories"]:
            if site_config["categories"].get(category) == None:
                site_config["categories"][category] = [front_matter.metadata]
            else:
                site_config["categories"][category] = site_config["categories"][category] + [front_matter.metadata]

    return site_config

def create_posts(is_retro, pages_created_count, site_config):
    post_files = posts

    previous_page = None

    for post_item in range(0, len(post_files)):
        post_file = post_files[post_item]

        f = post_directory + "/" + post_file

        # do not copy dotfiles into site
        if post_file.startswith("."):
            continue

        if len(post_files) < post_item + 1:
            next_post_url = post_directory + "/" + post_files[post_item + 1]

            next_post = frontmatter.load(next_post_url)
        else:
            next_post_url = None
            next_post = None

        site_config = process_page(post_directory, f, site_config, "post", previous_page, is_retro, next_post, next_post_url)

        previous_page = f

        pages_created_count += 1

    return site_config, pages_created_count

def main(is_retro):
    pages_created_count = 0

    site_config = config.site_config

    site_config, pages_created_count = create_posts(is_retro, pages_created_count, site_config)

    # get all directories in folder
    all_directories = os.listdir(BASE_DIR)

    site_config["posts"].reverse()

    site_config, pages_created_count = create_non_post_files(all_directories, is_retro, pages_created_count, site_config)

    os.mkdir("_site/category")

    site_config, pages_created_count = create_archives.create_category_pages(site_config, BASE_DIR, OUTPUT, pages_created_count)

    site_config, pages_created_count = create_archives.create_pagination_pages(site_config, OUTPUT, pages_created_count)

    print(site_config["posts"])
    site_config, pages_created_count = create_archives.create_date_archive_pages(site_config, OUTPUT, pages_created_count)

    site_config, pages_created_count = create_archives.create_list_pages(BASE_DIR, site_config, OUTPUT, pages_created_count)

    site_config = create_archives.generate_sitemap(site_config, OUTPUT)

    # feeds.create_feeds(site_config)

    if os.path.exists("assets"):
        shutil.copytree("assets", "_site/assets")

    print("Pages generated: " + str(pages_created_count))

    per_second = str(pages_created_count / (datetime.datetime.now() - start_time).total_seconds())

    # round to 2 dp
    per_second = round(float(per_second), 2)

    print("Pages generated per second: " + per_second)

def slugify(post_path):
    return "".join([char for char in post_path.replace(" ", "-") if char.isalnum() or char in ALLOWED_SLUG_CHARS]).replace(".md", ".html")

if __name__ == "__main__":
    main(is_retro=False)

    end_time = datetime.datetime.now()

    time_taken = end_time - start_time

    print("Time taken to build website: " + str(time_taken))