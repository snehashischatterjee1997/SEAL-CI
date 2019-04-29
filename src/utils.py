import json
import glob
import torch
import pandas as pd
import numpy as np
from tqdm import tqdm
import networkx as nx
from texttable import Texttable

def hierarchical_graph_reader(path):
    """
    Reading the macro-level graph from disk.
    :param path: Path to the edge list.
    :return graph: Hierarchical graph as a NetworkX object.
    """
    edges = pd.read_csv(path).values.tolist()
    graph = nx.from_edgelist(edges)
    return graph

def graph_level_reader(path):
    """
    Reading a single graph from disk.
    :param path: Path to the JSON file.
    :return data: Dictionary of data.
    """
    data = json.load(open(path))
    return data

def tab_printer(args):
    """
    Function to print the logs in a nice tabular format.
    :param args: Parameters used for the model.
    """
    args = vars(args)
    keys = sorted(args.keys())
    t = Texttable() 
    t.add_rows([["Parameter", "Value"]] + [[k.replace("_"," ").capitalize(),args[k]] for k in keys])
    print(t.draw())

def get_graph_labels_and_features(graph_files):
    """
    Creating feature and label maps.
    :param graph_files: Json filer list.
    :return features: Feature map.
    :return labels: Label map.
    """
    labels = set()
    features = set()
    for graph_file in tqdm(graph_files):
        data = json.load(open(graph_file))
        labels = labels.union(set([data["label"]]))
        features = features.union(set([val for k,v in data["features"].items() for val in v]))
    labels = {v:i for i,v in enumerate(labels)}
    features = {v:i for i,v in enumerate(features)}
    return features, labels

class GraphDatasetGenerator(object):

    def __init__(self, path):
        self.path = path
        self._enumerate_graphs()
        self._count_features_and_labels()
        self._create_target()
        self._create_dataset()

    def _enumerate_graphs(self):
        graph_count = len(glob.glob(self.path + "*.json"))
        labels = set()
        features = set()
        self.graphs = []
        for index in tqdm(range(graph_count)):
            graph_file = self._concatenate_name(index)
            data = graph_level_reader(graph_file)
            self.graphs.append(data)
            labels = labels.union(set([data["label"]]))
            features = features.union(set([val for k,v in data["features"].items() for val in v]))
        self.label_map = {v:i for i,v in enumerate(labels)}
        self.feature_map = {v:i for i,v in enumerate(features)}

    def _count_features_and_labels(self):
        self.number_of_features = len(self.feature_map)
        self.number_of_labels = len(self.label_map)

    def _transform_edges(self, raw_data):
        """
        """
        return torch.t(torch.LongTensor(raw_data["edges"]))

    def _concatenate_name(self, index):
        return self.path + str(index) + ".json"

    def _transform_features(self, raw_data):
        """
        """
        number_of_nodes = len(raw_data["features"])
        feature_matrix = np.zeros((number_of_nodes, self.number_of_features))
        index_1 = [int(node) for node, features in raw_data["features"].items() for feature in features]
        index_2 = [int(self.feature_map[feature]) for node, features in raw_data["features"].items() for feature in features]
        feature_matrix[index_1, index_2] = 1.0
        feature_matrix = torch.FloatTensor(feature_matrix)
        return feature_matrix

    def _data_transform(self, raw_data):
        clean_data = dict()
        clean_data["edges"] = self._transform_edges(raw_data)
        clean_data["features"] = self._transform_features(raw_data)
        return clean_data

    def _create_target(self):
        """
        Creating a target vector.
        """
        self.target = [graph["label"] for graph in self.graphs]
        self.target = torch.LongTensor(self.target)

    def _create_dataset(self):
        """
        Creating a list of dictionaries with edge list matrices and feature matrices.
        """
        self.graphs = [self._data_transform(graph) for graph in self.graphs]
