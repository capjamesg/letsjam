import concurrent.futures
import datetime
import os

import frontmatter
import jinja2

from app import create_template


def list_archive_date(date):
    if type(date) is str and "." in date:
        date = date.replace(" ", "T")
        date = datetime.datetime.strptime(date, "%Y-%m-%dT%H:%M:%S.%f")
    elif type(date) is str:
        date = date.replace(" ", "T")
        date = datetime.datetime.strptime(date, "%Y-%m-%dT%H:%M:%S-00:00")

    return date


def long_date(date):
    return list_archive_date(date).strftime("%B %d, %Y")


def date_to_xml_string(date):
    return list_archive_date(date).strftime("%Y-%m-%dT%H:%M:%S")


def archive_date(date):
    return list_archive_date(date).strftime("%Y/%m")


def slugify(post_path):
    return "".join(
        [
            char
            for char in post_path.replace(" ", "-")
            if char.isalnum() or char in ["-", "/", ".", "_"]
        ]
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
    page_path_base,
):

    paginator = {
        "total_pages": number_of_pages,
        "previous_page": increment - 1,
        "next_page": increment + 1,
        "next_page_path": page_path_base + str(increment + 1),
        "current_page": increment + 1
    }

    if increment - 1 <= 0:
        paginator["previous_page_path"] = page_path_base
    else:
        paginator["previous_page_path"] = page_path_base + str(increment - 1)

    posts = entries[increment * 10 : increment * 10 + 10]

    page = {
        "title": f"Entries for {date}",
        "date": date,
        "posts": posts,
        "url": output + date + "/" + str(increment + 1) + "/",
    }

    rendered_string = create_template(
        template_path, site=site_config, category=date, page=page, paginator=paginator
    )

    print(f"Generating Archive Page {date} ({increment})")

    increment = str(increment + 1)

    if increment == "1":
        save_archive_file(
            output + "/" + date + "/",
            output + "/" + date + "/",
            increment,
            rendered_string,
        )
    else:
        save_archive_file(
            output + "/" + date + "/" + increment + "/",
            output + "/" + date + "/",
            increment,
            rendered_string,
        )

    pages_created_count += 1

    return pages_created_count


def create_category_pages(
    site_config, output, pages_created_count, page_type="category"
):
    """
    Creates category pages for each category specified in post "categories" values.
    """

    if page_type == "category":
        iterator = site_config["categories"].items()
        layout = "category.html"
    else:
        iterator = site_config["tags"].items()
        layout = "tag.html"

    for category, entries in iterator:
        front_matter = frontmatter.loads(site_config["layouts"][layout])

        template_name = front_matter["layout"]

        number_of_pages = int(len(entries) / 10) + 1

        slug = (
            category.lower()
            .replace(" ", "-")
            .replace("(", "")
            .replace(")", "")
            .replace("'", "")
        )

        for increment in range(0, number_of_pages):
            paginator = {
                "total_pages": number_of_pages,
                "previous_page": increment - 1,
                "next_page": increment + 1,
                "previous_page_path": f"/{page_type}/"
                + slug
                + "/"
                + str(increment - 1)
                + "/",
                "next_page_path": f"/{page_type}/"
                + slug
                + "/"
                + str(increment + 1)
                + "/",
                "current_page": increment + 1
            }

            if increment - 1 <= 0:
                paginator["previous_page_path"] = f"/{page_type}/" + slug + "/2/"
            else:
                paginator["previous_page_path"] = (
                    f"/{page_type}/" + slug + "/" + str(increment - 1) + "/"
                )

            if increment + 1 == number_of_pages:
                paginator["next_page_path"] = ""
                paginator["next_page"] = 0
            else:
                paginator["next_page_path"] = (
                    "/category/" + slug + "/" + str(increment + 1) + "/"
                )

            template_string = site_config["layouts"][template_name + ".html"]

            loader = jinja2.FileSystemLoader(searchpath="./")

            page = {
                "title": category,
                "category": category,
                "posts": entries[increment * 10 : increment * 10 + 10],
                "url": f"/{page_type}/" + slug + "/" + str(increment) + "/",
                "number": increment,
            }

            dates = {}

            for i in range(0, 365):
                dates[
                    (datetime.datetime.now() - datetime.timedelta(days=i)).strftime(
                        "%Y-%m-%d"
                    )
                ] = 0

            for post in entries:
                if post["full_date"] != "":
                    date = datetime.datetime.strptime(
                        post["full_date"], "%Y-%m-%d %H:%M:%S-00:00"
                    ).strftime("%Y-%m-%d")
                else:
                    date = ""

                if dates.get(date) is not None:
                    dates[date] += 1

            values = dates.values()

            # convert values to list
            data_points = list(values)

            data_points.reverse()

            number_of_posts = len(entries)

            sparkline = f"""<p>There are {number_of_posts} Posts in this {page_type}<br><embed src="/assets/sparkline.svg?{','.join([str(val) for val in data_points])}" height=45></p>"""

            page["sparkline"] = sparkline

            rendered_front_matter = jinja2.Environment(loader=loader)

            # register filter
            rendered_front_matter.filters["long_date"] = long_date
            rendered_front_matter.filters["date_to_xml_string"] = date_to_xml_string
            rendered_front_matter.filters["archive_date"] = archive_date
            rendered_front_matter.filters["list_archive_date"] = list_archive_date

            rendered_front_matter = rendered_front_matter.from_string(
                front_matter.content
            ).render(
                site=site_config, category=category, page=page, paginator=paginator
            )

            main_page_content = jinja2.Environment(loader=loader)

            # register filter
            main_page_content.filters["long_date"] = long_date
            main_page_content.filters["date_to_xml_string"] = date_to_xml_string
            main_page_content.filters["archive_date"] = archive_date
            main_page_content.filters["list_archive_date"] = list_archive_date

            main_page_content = main_page_content.from_string(template_string).render(
                page=page,
                category=category,
                site=site_config,
                content=rendered_front_matter,
                paginator=paginator,
            )

            print(f"Generating {category} {page_type} Page")

            increment = str(increment)

            slug = (
                category.lower()
                .replace(" ", "-")
                .replace("(", "")
                .replace(")", "")
                .replace("'", "")
            )

            save_archive_file(
                output + f"/{page_type}/" + slug + "/" + increment + "/",
                output + f"/{page_type}/" + slug + "/",
                increment,
                main_page_content,
            )

            pages_created_count += 1

    return site_config, pages_created_count


def create_list_pages(base_dir, site_config, output, pages_created_count):
    """
    Creates pages for specified groups (i.e. "likes").
    """
    list_pages = [
        "likes",
        "bookmarks",
        "replies",
        "notes",
        "flights",
        "events",
        "checkins",
        "photos",
    ]

    for page in list_pages:
        number_of_pages = int(len(site_config[page]) / 10) + 1

        # reverse so posts are in reverse chronological order
        site_config[page].reverse()

        for increment in range(0, number_of_pages):
            paginator = {
                "total_pages": number_of_pages,
                "previous_page": increment - 1,
                "next_page": increment + 1,
                "previous_page_path": "/" + page + "/" + str(increment - 1) + "/",
                "next_page_path": "/" + page + "/" + str(increment + 1) + "/",
                "current_page": increment + 1
            }

            if increment - 1 <= 0:
                paginator["previous_page_path"] = "/" + page + "/"
            else:
                paginator["previous_page_path"] = (
                    "/" + page + "/" + str(increment - 1) + "/"
                )

            posts = site_config[page][increment * 10 : increment * 10 + 10]

            template = create_template(
                base_dir + "/templates/" + page + ".html",
                page={"posts": posts, "title": page.title(), "url": "/" + page + "/"},
                site=site_config,
                paginator=paginator,
            )

            print(f"Generating {page} List Page")

            increment = str(increment)

            save_archive_file(
                output + "/" + page + "/" + increment + "/",
                output + "/" + page + "/",
                increment,
                template,
            )

            pages_created_count += 1

    return site_config, pages_created_count


def create_date_archive_pages(site_config, output, pages_created_count, posts):
    """
    Creates pages that lists posts by the day, month and year in which they were published.
    """
    all_posts = {}

    for post in posts:
        date = post["url"].split("/")

        if len(date) < 4:
            continue

        year = date[1].strip()
        month = date[2].strip()
        day = date[3].strip()

        if not year.isdigit() or not month.isdigit():
            continue

        date = f"{year}/{month}-{day}"

        if all_posts.get(f"{year}-{month}-{day}") is None:
            all_posts[f"{year}-{month}-{day}"] = [post]
        else:
            all_posts[f"{year}-{month}-{day}"] = all_posts[f"{year}-{month}-{day}"] + [
                post
            ]

        if all_posts.get(f"{year}-{month}") is None:
            all_posts[f"{year}-{month}"] = [post]
        else:
            all_posts[f"{year}-{month}"] = all_posts[f"{year}-{month}"] + [post]

        if all_posts.get(year) is None:
            all_posts[year] = [post]
        else:
            all_posts[year] = all_posts[year] + [post]

    archive_object = {"years": {}}

    year_month_combinations = {}

    # generate posts by date archive pages
    for date, entries in all_posts.items():
        entry_count = len(entries)
        number_of_pages = int(entry_count / 10) + 1

        original_date = date

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
                    date + "/",
                )
                for increment in range(0, number_of_pages)
            ]

            for _ in concurrent.futures.as_completed(future_to_page):
                try:
                    pages_created_count += 1
                except Exception as exc:
                    print(f"{date} generated an exception: {exc}")

        if len(original_date) > 4:
            month = original_date.split("-")[1]
            year = original_date.split("-")[0]

            written_month = datetime.datetime.strptime(month, "%m").strftime("%B")

            month_object = {"written": written_month, "numeric": month}

            if year_month_combinations.get(year + "-" + month) is None:
                year_month_combinations[year + "-" + month] = [date]

                if archive_object["years"].get(year) is None:
                    archive_object["years"][year] = [month_object]
                else:
                    archive_object["years"][year] = archive_object["years"][year] + [
                        month_object
                    ]

    print("Generating Archive Page at /archive/")

    if os.path.exists("templates/archive.html"):
        rendered_string = create_template(
            "templates/archive.html",
            site=site_config,
            page={"years": archive_object["years"], "url": "/archive/"},
            paginator=None,
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

    sitemap = create_template(
        "templates/sitemap.xml",
        base_url=site_config["baseurl"],
        pages=site_config["pages"],
        lastmod=lastmod,
    )

    with open(slugify(output + "/sitemap.xml"), "w+") as file:
        file.write(sitemap)
