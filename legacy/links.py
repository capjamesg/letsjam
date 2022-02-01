import json

import matplotlib.pyplot as plt
import networkx as nx

Graph = nx.Graph()

# load data

with open("all_links.json", "r") as f:
    for l in f.readlines():
        data = json.loads(l)

        data["dst"] = data["dst"].split("/")[2].lower()

        Graph.add_node(data["dst"])

        if data["classes"] == None:
            classes = "a"
        else:
            classes = data["classes"][0]

        print(classes)

        Graph.add_edge(classes, data["dst"])

nx.draw(Graph, pos=nx.spring_layout(Graph), with_labels=True)

plt.title("jamesg.blog Network Graph")

plt.show()
