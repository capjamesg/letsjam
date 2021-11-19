# test code to make template generation more efficient

import jinja2
import frontmatter

# open templates/index.html file

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

template = create_template("templates/index.html", site={"posts": []}, page={"posts": []}, content=[], paginator=[])