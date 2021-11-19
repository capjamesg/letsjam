from flask import Flask, render_template, send_from_directory

app = Flask(__name__, template_folder="_site")

@app.route("/<path:path>")
def index(path):
    path = path.rstrip("/") + ".html"
    print(path)
    return send_from_directory("_site", path)

@app.route("/assets/<path:path>")
def render_assets(path):
    return send_from_directory("_site/assets", path)

@app.route("/assets/styles/<path:path>")
def render_styles(path):
    return send_from_directory("_site/assets/styles", path)

if __name__ == "__main__":
    app.run(debug=True)