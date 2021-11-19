import create_archives
import feeds
from config import site_config, BASE_DIR, OUTPUT, ALLOWED_SLUG_CHARS
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

def create_non_post_files(all_directories, is_retro):
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
                process_page(directory_name, f, None, None, is_retro)
            else:
                shutil.copy(f, OUTPUT + "/" + file_name)

def create_template(path, **kwargs):
    template_front_matter = frontmatter.load(path)

    loader = jinja2.FileSystemLoader(searchpath="./")

    template = jinja2.Environment(loader=loader)

    new_template = template.from_string(template_front_matter.content)

    if template_front_matter.metadata["layout"]:
        parent_front_matter = frontmatter.load("_layouts/" + template_front_matter.metadata["layout"] + ".html")
        parent_template = template.from_string(parent_front_matter.content)

        kwargs["content"] = new_template.render(**kwargs)

        template = parent_template.render(kwargs)

        if parent_front_matter.metadata.get("layout"):
            parent_template = create_template("_layouts/" + parent_front_matter.metadata["layout"] + ".html", **kwargs)
    else:
        template = new_template.render(kwargs)
    
    return template
    
def process_page(directory_name, file_name, page_type=None, previous_page=None, is_retro=False, next_post=None, next_post_url=None):
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
        ("Repost", "reposts"),
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

    loader = jinja2.FileSystemLoader(searchpath="./")

    main_page, template_front_matter = create_template(front_matter)

    rendered_main_page = main_page.render(site=site_config, page=front_matter.metadata)

    template_name = front_matter["layout"]

    with open(directory_name + "/../_layouts/" + template_name + ".html") as template_file:
        template_string = template_file.read()

    template_front_matter = frontmatter.load(directory_name + "/../_layouts/" + template_name + ".html")

    template, template_front_matter = create_template(template_front_matter)

    rendered_string = template.render(site=site_config, page=front_matter.metadata, content=rendered_main_page, paginator=None)

    if template_front_matter.get("layout"):
        template_front_matter = frontmatter.load(directory_name + "/../_layouts/" + template_front_matter["layout"] + ".html")

        template = create_template(template_front_matter)

        template_string = template.render(site=site_config, page=front_matter.metadata, content=rendered_string, paginator=None)

    if is_retro == True:
        template_string = template_string.replace('{% includes "navigation.html"}', '{% includes "retro_sidebar.html"}').replace('{% includes "footer.html"}', '')

    template = jinja2.Environment(loader=loader).from_string(template_string)

    rendered_string = template.render(page=front_matter.metadata, content=rendered_main_page, site=site_config, paginator=None)

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

    if page_type == "post":
        site_config["posts"] = site_config["posts"] + [front_matter.metadata]

        for category in front_matter.metadata["categories"]:
            if site_config["categories"].get(category) == None:
                site_config["categories"][category] = [front_matter.metadata]
            else:
                site_config["categories"][category] = site_config["categories"][category] + [front_matter.metadata]

def create_posts(is_retro):
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

        process_page(post_directory, f, "post", previous_page, is_retro, next_post, next_post_url)

        previous_page = f

def main(is_retro):
    create_posts(is_retro)

    # get all directories in folder
    all_directories = os.listdir(BASE_DIR)

    site_config["posts"].reverse()

    create_non_post_files(all_directories, is_retro)

    os.mkdir("_site/category")

    create_archives.create_category_pages(site_config, BASE_DIR, OUTPUT)

    create_archives.create_pagination_pages(site_config, OUTPUT)

    create_archives.create_date_archive_pages(site_config, OUTPUT)

    create_archives.create_list_pages(BASE_DIR, site_config, OUTPUT)

    feeds.create_feeds(site_config)

    if os.path.exists("assets"):
        shutil.copytree("assets", "_site/assets")

def slugify(post_path):
    return "".join([char for char in post_path.replace(" ", "-") if char.isalnum() or char in ALLOWED_SLUG_CHARS]).replace(".md", ".html")

if __name__ == "__main__":
    main(is_retro=False)

    end_time = datetime.datetime.now()

    time_taken = end_time - start_time

    print("Time taken to build website: " + str(time_taken))