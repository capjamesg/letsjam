import os
import datetime
import frontmatter
import jinja2
import concurrent.futures
from app import create_template
from config import ALLOWED_SLUG_CHARS

def long_date(date):
    if type(date) is str:
        date = datetime.datetime.strptime(date, "%Y-%m-%dT%H:%M:%S-00:00")

    return date.strftime("%B %d, %Y")

def date_to_xml_string(date):
    if type(date) is str:
        date = datetime.datetime.strptime(date, "%Y-%m-%dT%H:%M:%S-00:00")
        
    return date.strftime("%Y-%m-%dT%H:%M:%S")

def archive_date(date):
    if type(date) is str:
        date = datetime.datetime.strptime(date, "%Y-%m-%dT%H:%M:%S-00:00")

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
        "title": f"Entries for {date}",
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

    print(f"Generating Archive Page {date} ({increment})")

    increment = str(increment + 1)

    save_archive_file(
        output + "/archive/" + date + "/" + increment + "/",
        output + "/archive/" + date + "/",
        increment,
        rendered_string
    )

    pages_created_count += 1

    return pages_created_count

def create_pagination_pages(site_config, output, pages_created_count, entries, category):
    number_of_pages = int(len(entries) / 10) + 1

    for page in range(0, number_of_pages):
        paginator = {
            "total_pages": number_of_pages,
            "previous_page": page - 1,
            "next_page": page + 1,
        }

        slug = category.lower().replace(" ", "-").replace("(", "").replace(")", "").replace("'", "")

        increment_value = page + 1

        if increment_value - 1 <= 0:
            paginator["previous_page_path"] = "/category/" + slug.lower() + "/"
            paginator["next_page_path"] = "/category/" + slug.lower() + "/2/"
        else:
            paginator["previous_page_path"] = "/category/" + slug.lower() + "/" + str(increment_value - 1) + "/"
            paginator["next_page_path"] = "/category/" + slug.lower() + "/" + str(increment_value + 1) + "/"

        page_contents = site_config

        page_contents["posts"] = entries[page * 10:page * 10 + 10]
        page_contents["category"] = category
        page_contents["url"] = "/" + slug + "/" + str(page) + "/"

        template = create_template(
            "_layouts/category.html",
            page=page_contents,
            category=slug,
            site=site_config,
            paginator=paginator
        )

        path_to_save = output + "/" + "category/" + category.lower() + "/" + str(page + 1) + "/"

        path_to_save = slugify("/".join(path_to_save.split("/")[:-1]))

        if not os.path.exists(path_to_save):
            os.makedirs(path_to_save)

        print(f"Generating {category} Archive Page ({path_to_save})")

        with open(slugify(path_to_save + "/index.html"), "w+") as file:
            file.write(template)

        pages_created_count += 1

    return site_config, pages_created_count

def create_category_pages(site_config, output, pages_created_count, page_type="category"):
    """
        Creates category pages for each category specified in post "categories" values.
    """

    if page_type == "category":
        iterator = site_config["categories"].items()
    else:
        iterator = site_config["tags"].items()

    for category, entries in iterator:
        front_matter = frontmatter.loads(site_config["layouts"]["category.html"])

        template_name = front_matter["layout"]

        number_of_pages = int(len(entries) / 10) + 1

        slug = category.lower().replace(" ", "-").replace("(", "").replace(")", "").replace("'", "")

        for increment in range(0, number_of_pages):
            paginator = {
                "total_pages": number_of_pages,
                "previous_page": increment - 1,
                "next_page": increment + 1,
                "previous_page_path": f"/{page_type}/" + slug + "/" + str(increment - 1) + "/",
                "next_page_path": f"/{page_type}/" + slug + "/" + str(increment + 1) + "/"
            }

            if increment - 1 <= 0:
                paginator["previous_page_path"] = f"/{page_type}/" + slug + "/2/"
            else:
                paginator["previous_page_path"] = f"/{page_type}/" + slug + "/" + str(increment - 1) + ".html"

            template_string = site_config["layouts"][template_name + ".html"]
            
            loader = jinja2.FileSystemLoader(searchpath="./")

            page = {
                "title": category,
                "category": category,
                "posts": entries[increment * 10:increment * 10 + 10],
                "url": f"/{page_type}/" + slug + "/" + str(increment) + ".html",
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

            print(f"Generating {category} {page_type} Page")

            increment = str(increment)

            category = category.lower().replace(" ", "-").replace("(", "").replace(")", "").replace("'", "")

            save_archive_file(
                output + f"/{page_type}/" + category + "/" + increment + "/",
                output + f"/{page_type}/" + category + "/",
                increment,
                main_page_content
            )

            pages_created_count += 1

    return site_config, pages_created_count

def create_list_pages(base_dir, site_config, output, pages_created_count):
    """
        Creates pages for specified groups (i.e. "likes").
    """
    list_pages = ["likes", "bookmarks", "webmentions", "notes"]
    
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

            print(f"Generating {page} List Page")

            increment = str(increment)

            save_archive_file(
                output + "/" + page + "/" + increment + "/",
                output + "/" + page + "/",
                increment,
                template
            )

            pages_created_count += 1

    template = create_template(
        base_dir + "/templates/all_likes.html",
        page={"posts": site_config["likes"], "url": "/likes/all/"},
        site=site_config,
        paginator=paginator
    )

    print(f"Generating {page} Archive Page")

    with open("_site/likes/all/index.html", "w+") as file:
        file.write(template)

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

        date = f"{year}/{month}"

        if posts_by_date.get(f"{year}-{month}") == None:
            posts_by_date[f"{year}-{month}"] = [post]
        else:
            posts_by_date[f"{year}-{month}"] = posts_by_date[f"{year}-{month}"] + [post]

        if posts_by_year.get(year) == None:
            posts_by_year[year] = [post]
        else:
            posts_by_year[year] = posts_by_year[year] + [post]

    # generate posts by date archive pages
    for date, entries in posts_by_date.items():
        entry_count = len(entries)
        number_of_pages = int(entry_count / 10) + 1

        date = date.replace("-", "/")

        with concurrent.futures.ThreadPoolExecutor(max_workers=15) as executor:
            future_to_page = [
                executor.submit(
                    generate_archive_page,
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
                for increment in range(0, number_of_pages)
            ]

            for future in concurrent.futures.as_completed(future_to_page):
                try:
                    pages_created_count += 1
                except Exception as exc:
                    print(f"{date} generated an exception: {exc}")

    # generate posts by year archive pages
    for date, entries in posts_by_year.items():
        # create different pages
        entry_count = len(entries)
        number_of_pages = int(entry_count / 10) + 1

        with concurrent.futures.ThreadPoolExecutor(max_workers=15) as executor:
            future_to_page = [
                executor.submit(
                    generate_archive_page,
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
                for increment in range(0, number_of_pages)
            ]

            for future in concurrent.futures.as_completed(future_to_page):
                try:
                    pages_created_count += 1
                except Exception as exc:
                    print(f"{date} generated an exception: {exc}")

    archive_object = {
        "years": {}
    }

    for item in posts_by_date.keys():
        year = item.split("-")[0]
        month = item.split("-")[1]

        written_month = datetime.datetime.strptime(month, "%m").strftime("%B")

        month_object = {
            "written": written_month,
            "numeric": month
        }

        if archive_object["years"].get(year) == None:
            archive_object["years"][year] = [month_object]
        else:
            archive_object["years"][year] = archive_object["years"][year] + [month_object]

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