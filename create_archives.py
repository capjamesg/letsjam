from feedgen.feed import FeedGenerator
from app import create_template
import frontmatter
import datetime
import jinja2
import os

allowed_slug_chars = ["-", "/", ".", "_"]

def long_date(date):
    return date.strftime("%B %d, %Y")

def date_to_xml_string(date):
    return date.strftime("%Y-%m-%dT%H:%M:%S")

def slugify(post_path):
    return "".join([char for char in post_path.replace(" ", "-") if char.isalnum() or char in allowed_slug_chars]).replace(".md", ".html")

def create_pagination_pages(site_config, output, pages_created_count):
    for category, entries in site_config["categories"].items():
        number_of_pages = int(len(entries) / 10) + 1

        for page in range(0, number_of_pages):
            page_contents = site_config

            page_contents["posts"] = entries[page * 10:page * 10 + 10]
            page_contents["category"] = category

            template = create_template("_layouts/category.html", page=page_contents, category=category, site=site_config, paginator=None)

            path_to_save = output + "/" + "category/" + category.lower() + "/" + str(page + 1) + ".html"

            if not os.path.exists(slugify("/".join(path_to_save.split("/")[:-1]))):
                os.makedirs(slugify("/".join(path_to_save.split("/")[:-1])))

            print("Generating {} Archive Page ({})".format(category, path_to_save))

            with open(slugify(path_to_save), "w+") as file:
                file.write(template)

            pages_created_count += 1

    return site_config, pages_created_count

def create_category_pages(site_config, base_dir, output, pages_created_count):
    for category, entries in site_config["categories"].items():
        entries.reverse()
        front_matter = frontmatter.load("_layouts/category.html")

        template_name = front_matter["layout"]

        number_of_pages = int(len(entries) / 10) + 1

        for increment in range(0, number_of_pages):
            paginator = {
                "total_pages": number_of_pages,
                "previous_page": increment - 1,
                "next_page": increment + 1,
                "previous_page_path": "/category/" + category.lower() + "/" + str(increment - 1) + ".html",
                "next_page_path": "/category/" + category.lower() + "/" + str(increment + 1) + ".html"
            }
            with open(base_dir + "/_layouts/" + template_name + ".html") as template_file:
                template_string = template_file.read()
            
            loader = jinja2.FileSystemLoader(searchpath="./")

            page = {
                "title": category,
                "category": category,
                "posts": entries[increment * 10:increment * 10 + 10]
            }

            rendered_front_matter = jinja2.Environment(loader=loader)

            # register filter
            rendered_front_matter.filters["long_date"] = long_date
            rendered_front_matter.filters["date_to_xml_string"] = date_to_xml_string

            rendered_front_matter = rendered_front_matter.from_string(front_matter.content)\
                .render(
                    site=site_config,
                    category=category,
                    page=page,
                    paginator=paginator
                )

            main_page_content = jinja2.Environment(loader=loader)

            # register filter
            main_page_content.filters["long_date"] = long_date
            main_page_content.filters["date_to_xml_string"] = date_to_xml_string

            main_page_content = main_page_content.from_string(template_string)\
                .render(
                    page=page,
                    category=category,
                    site=site_config,
                    content=rendered_front_matter,
                    paginator=paginator
                )

            print("Generating {} Category Page".format(category))

            increment = str(increment)

            category = category.lower()

            if int(increment) > 0:
                if not os.path.exists(slugify(output + "/category/" + category + "/" + increment + "/")):
                    os.makedirs(slugify(output + "/category/" + category + "/" + increment + "/"))

                with open(slugify(output + "/category/" + category + "/" + increment + "/index.html"), "w+") as file:
                    file.write(main_page_content)
            else:
                if not os.path.exists(slugify(output + "/category/" + category + "/")):
                    os.makedirs(slugify(output + "/category/" + category + "/"))

                with open(slugify(output + "/category/" + category) + "/index.html", "w+") as file:
                    file.write(main_page_content)

            pages_created_count += 1

    return site_config, pages_created_count

def create_list_pages(base_dir, site_config, output, pages_created_count):
    list_pages = ["likes", "bookmarks", "replies", "rsvps", "coffee"]
    
    for page in list_pages:
        number_of_pages = int(len(site_config[page]) / 10) + 1

        for increment in range(0, number_of_pages):
            paginator = {
                "total_pages": number_of_pages,
                "previous_page": increment - 1,
                "next_page": increment + 1,
                "previous_page_path": "/" + page + "/" + str(increment - 1) + ".html",
                "next_page_path": "/" + page + "/" + str(increment + 1) + ".html"
            }

            posts = site_config[page][increment * 10:increment * 10 + 10]

            template = create_template(base_dir + "/templates/" + page + ".html", page={"posts": posts}, site=site_config, paginator=paginator)

            print("Generating {} List Page".format(page))

            increment = str(increment)

            print(slugify(output + "/" + page + "/" + increment + "/index.html"))

            if int(increment) > 0:
                if not os.path.exists(slugify(output + "/" + page + "/" + increment + "/")):
                    os.makedirs(slugify(output + "/" + page + "/" + increment + "/"))

                with open(slugify(output + "/" + page + "/" + increment + "/index.html"), "w+") as file:
                    file.write(template)
            else:
                if not os.path.exists(slugify(output + "/" + page + "/")):
                    os.makedirs(slugify(output + "/" + page + "/"))

                with open(output + "/" + page + "/index.html", "w+") as file:
                    file.write(template)

            pages_created_count += 1

    return site_config, pages_created_count

def create_date_archive_pages(site_config, output, pages_created_count, posts):
    posts_by_date = {}
    posts_by_year = {}

    for post in posts:
        date = post["url"].split("/")

        if len(date) < 3:
            continue

        year = date[1].strip()
        month = date[2].strip()

        print(year, month)

        if not year.isdigit() or not month.isdigit():
            continue

        date = "{}/{}".format(year, month)

        if posts_by_date.get("{}-{}".format(year, month)) == None:
            posts_by_date["{}-{}".format(year, month)] = [post]
        else:
            posts_by_date["{}-{}".format(year, month)] = posts_by_date["{}-{}".format(year, month)] + [post]

        if posts_by_year.get(year) == None:
            posts_by_year[year] = [post]
        else:
            posts_by_year[year] = posts_by_year[year] + [post]

    for date, entries in posts_by_date.items():
        rendered_string = create_template("_layouts/category.html", site=site_config, category=date, page={"title": "Entries for {}".format(date), "posts": entries}, paginator=None)

        print("Generating {} Archive Page".format(date))

        pages_created_count += 1

        date = date.split("/")[-1].replace("-", "/").lower()

        if not os.path.exists(output + "/" + date):
            os.makedirs(output + "/" + date)

        with open(slugify(output + "/" + date + "/index.html"), "w+") as file:
            file.write(rendered_string)

    for date, entries in posts_by_year.items():
        rendered_string = create_template("_layouts/category.html", site=site_config, category=date, page={"title": "Entries for {}".format(date), "posts": entries}, paginator=None)

        print("Generating {} Archive Page".format(date))

        pages_created_count += 1

        date = date.lower()

        if not os.path.exists(output + "/" + date):
            os.makedirs(output + "/" + date)

        with open(slugify(output + "/" + date + "/index.html"), "w+") as file:
            file.write(rendered_string)

    return site_config, pages_created_count

def generate_sitemap(site_config, output):
    lastmod = datetime.datetime.now().strftime("%Y-%m-%d")

    sitemap = create_template("templates/sitemap.xml", pages=site_config["pages"], lastmod=lastmod)

    with open(slugify(output + "/sitemap.xml"), "w+") as file:
        file.write(sitemap)