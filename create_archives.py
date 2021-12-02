import os
import datetime
import frontmatter
import jinja2
from app import create_template
from config import ALLOWED_SLUG_CHARS

def long_date(date):
    return date.strftime("%B %d, %Y")

def date_to_xml_string(date):
    return date.strftime("%Y-%m-%dT%H:%M:%S")

def archive_date(date):
    return date.strftime("%Y/%m")

def slugify(post_path):
    return "".join(
        [char for char in post_path.replace(" ", "-") if char.isalnum() or char in ALLOWED_SLUG_CHARS]
    ).replace(".md", ".html")

def save_archive_file(first_page_path, future_path, increment, page_to_save):
    if int(increment) > 0:
        if not os.path.exists(slugify(first_page_path)):
            os.makedirs(slugify(first_page_path))

        with open(slugify(first_page_path + "index.html"), "w+") as file:
            file.write(page_to_save)
    else:
        if not os.path.exists(slugify(future_path)):
            os.makedirs(slugify(future_path))

        with open(slugify(future_path) + "index.html", "w+") as file:
            file.write(page_to_save)

def generate_archive_page(
        increment,
        pages_created_count,
        template_path,
        entries,
        number_of_pages,
        date,
        site_config,
        output,
        page_path_base
    ):

    paginator = {
        "total_pages": number_of_pages,
        "previous_page": increment - 1,
        "next_page": increment + 1,
        "next_page_path": page_path_base + str(increment + 1)
    }

    if increment - 1 <= 0:
        paginator["previous_page_path"] = page_path_base
    else:
        paginator["previous_page_path"] = page_path_base + str(increment - 1)

    posts = entries[increment * 10:increment * 10 + 10]

    page = {
        "title": "Entries for {}".format(date),
        "date": date,
        "posts": posts,
        "url": output + "/archive/" + date + "/" + str(increment + 1) + "/"
    }

    rendered_string = create_template(
        template_path,
        site=site_config,
        category=date,
        page=page,
        paginator=paginator
    )

    print("Generating Archive Page {} ({})".format(date, increment))

    increment = str(increment + 1)

    save_archive_file(
        output + "/archive/" + date + "/" + increment + "/",
        output + "/archive/" + date + "/",
        increment,
        rendered_string
    )

    pages_created_count += 1

    return pages_created_count

def create_pagination_pages(site_config, output, pages_created_count):
    for category, entries in site_config["categories"].items():
        number_of_pages = int(len(entries) / 10) + 1

        for page in range(0, number_of_pages):
            paginator = {
                "total_pages": number_of_pages,
                "previous_page": page - 1,
                "next_page": page + 1,
            }

            increment_value = page + 1

            if increment_value - 1 <= 0:
                paginator["previous_page_path"] = "/category/" + category.lower() + "/"
                paginator["next_page_path"] = "/category/" + category.lower() + "/1/"
            else:
                paginator["previous_page_path"] = "/category/" + category.lower() + "/" + str(increment_value - 1) + "/"
                paginator["next_page_path"] = "/category/" + category.lower() + "/" + str(increment_value - 1) + "/"

            page_contents = site_config

            page_contents["posts"] = entries[page * 10:page * 10 + 10]
            page_contents["category"] = category
            page_contents["url"] = "/" + category + "/" + str(page) + "/"

            template = create_template(
                "_layouts/category.html",
                page=page_contents,
                category=category,
                site=site_config,
                paginator=paginator
            )

            path_to_save = output + "/" + "category/" + category.lower() + "/" + str(page + 1) + "/"

            path_to_save = slugify("/".join(path_to_save.split("/")[:-1]))

            if not os.path.exists(path_to_save):
                os.makedirs(path_to_save)

            print("Generating {} Archive Page ({})".format(category, path_to_save))

            with open(slugify(path_to_save + "/index.html"), "w+") as file:
                file.write(template)

            pages_created_count += 1

    return site_config, pages_created_count

def create_category_pages(site_config, base_dir, output, pages_created_count):
    """
        Creates category pages for each category specified in post "categories" values.
    """
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

            if increment - 1 <= 0:
                paginator["previous_page_path"] = "/category/" + category.lower() + "/"
            else:
                paginator["previous_page_path"] = "/category/" + category.lower() + "/" + str(increment - 1) + ".html"

            with open(base_dir + "/_layouts/" + template_name + ".html") as template_file:
                template_string = template_file.read()
            
            loader = jinja2.FileSystemLoader(searchpath="./")

            page = {
                "title": category,
                "category": category,
                "posts": entries[increment * 10:increment * 10 + 10],
                "url": "/category/" + category.lower() + "/" + str(increment) + ".html",
            }

            rendered_front_matter = jinja2.Environment(loader=loader)

            # register filter
            rendered_front_matter.filters["long_date"] = long_date
            rendered_front_matter.filters["date_to_xml_string"] = date_to_xml_string
            rendered_front_matter.filters["archive_date"] = archive_date

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
            main_page_content.filters["archive_date"] = archive_date

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

            save_archive_file(
                output + "/category/" + category + "/" + increment + "/",
                output + "/category/" + category + "/",
                increment,
                main_page_content
            )

            pages_created_count += 1

    return site_config, pages_created_count

def create_list_pages(base_dir, site_config, output, pages_created_count):
    """
        Creates pages for specified groups (i.e. "likes").
    """
    list_pages = ["likes", "bookmarks", "webmentions", "rsvps", "drinking"]
    
    for page in list_pages:
        number_of_pages = int(len(site_config[page]) / 10) + 1

        # reverse so posts are in reverse chronological order
        site_config[page].reverse()

        for increment in range(0, number_of_pages):
            paginator = {
                "total_pages": number_of_pages,
                "previous_page": increment - 1,
                "next_page": increment + 1,
                "previous_page_path": "/" + page + "/" + str(increment - 1),
                "next_page_path": "/" + page + "/" + str(increment + 1)
            }

            if increment - 1 <= 0:
                paginator["previous_page_path"] = "/" + page + "/"
            else:
                paginator["previous_page_path"] = "/" + page + "/" + str(increment - 1) + ".html"

            posts = site_config[page][increment * 10:increment * 10 + 10]

            template = create_template(
                base_dir + "/templates/" + page + ".html",
                page={"posts": posts, "title": page.title(), "url": "/" + page + "/"},
                site=site_config,
                paginator=paginator
            )

            print("Generating {} List Page".format(page))

            increment = str(increment)

            save_archive_file(
                output + "/" + page + "/" + increment + "/",
                output + "/" + page + "/",
                increment,
                template
            )

            pages_created_count += 1

    return site_config, pages_created_count

def create_date_archive_pages(site_config, output, pages_created_count, posts):
    """
        Creates pages that lists posts by the month and year in which they were published.
    """
    posts_by_date = {}
    posts_by_year = {}

    for post in posts:
        date = post["url"].split("/")

        if len(date) < 3:
            continue

        year = date[1].strip()
        month = date[2].strip()

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
        # create different pages
        entry_count = len(entries)
        number_of_pages = int(entry_count / 10) + 1

        date = date.replace("-", "/")

        for increment in range(0, number_of_pages):
            pages_created_count = generate_archive_page(
                increment,
                pages_created_count,
                "_layouts/date_archive.html",
                entries,
                number_of_pages,
                date,
                site_config,
                output,
                "/archive/" + date + "/" + str(increment - 1)
            )

    for date, entries in posts_by_year.items():
        # create different pages
        entry_count = len(entries)
        number_of_pages = int(entry_count / 10) + 1

        for increment in range(0, number_of_pages):
            pages_created_count = generate_archive_page(
                increment,
                pages_created_count,
                "_layouts/date_archive.html",
                entries,
                number_of_pages,
                date,
                site_config,
                output,
                "/archive/" + date + "/" + str(increment - 1)
            )

    archive_object = {
        "years": {}
    }

    for item in posts_by_date.keys():
        year = item.split("-")[0]
        month = item.split("-")[1]

        written_month = datetime.datetime.strptime(month, "%m").strftime("%B")

        if archive_object["years"].get(year) == None:
            archive_object["years"][year] = [written_month]
        else:
            archive_object["years"][year] = archive_object["years"][year] + [written_month]

    print("Generating Archive Page at /archive/")

    if os.path.exists("templates/archive.html"):
        rendered_string = create_template(
            "templates/archive.html",
            site=site_config,
            page={"years": archive_object["years"], "url": "/archive/"},
            paginator=None
        )

        if not os.path.exists(output + "/archive"):
            os.makedirs(output + "/archive")
                
        with open(slugify(output + "/archive" + "/index.html"), "w+") as file:
            file.write(rendered_string)

    return site_config, pages_created_count

def generate_sitemap(site_config, output):
    """
        Create sitemap.xml file.
    """
    lastmod = datetime.datetime.now().strftime("%Y-%m-%d")

    sitemap = create_template("templates/sitemap.xml", base_url=site_config["baseurl"], pages=site_config["pages"], lastmod=lastmod)

    with open(slugify(output + "/sitemap.xml"), "w+") as file:
        file.write(sitemap)