from .utils import *
from .cocmatrix import *


def network_plot(NetMatrix, normalize=None, n=None, degree=None, Title="Plot", type="auto", 
                 label=True, labelsize=1, label_cex=False, label_color=False, label_n=None, halo=False, 
                 cluster="walktrap", community_repulsion=0.1, vos_path=None, size=3, size_cex=False, 
                 curved=False, noloops=True, remove_multiple=True, remove_isolates=False, weighted=None, 
                 edgesize=1, edges_min=0, alpha=0.5, verbose=True):

    # Normalize column names to lowercase
    NetMatrix.columns = NetMatrix.index = NetMatrix.columns.str.lower()

    # Normalize similarity if required
    S = None
    bsk_S = None
    if normalize:
        S = normalize_similarity(NetMatrix, type=normalize)
        bsk_S = ig.Graph.Weighted_Adjacency(S.tolist(), mode=ig.ADJ_UNDIRECTED, attr="weight")
        bsk_S.vs["name"] = NetMatrix.columns

    # Create igraph object
    bsk_network = ig.Graph.Weighted_Adjacency(NetMatrix.values.tolist(), mode=ig.ADJ_UNDIRECTED, attr="weight")
    bsk_network.vs["name"] = NetMatrix.columns

    # Compute node degrees
    deg = np.array(bsk_network.degree())

    # PATCH: if graph has no nodes, return None immediately
    if len(bsk_network.vs) == 0 or len(deg) == 0:
        return None

    # Assign deg attribute to vertices
    bsk_network.vs["deg"] = deg.tolist()

    # Node sizes
    if size_cex:
        max_deg = max(deg) if max(deg) > 0 else 1
        bsk_network.vs["size"] = (deg / max_deg * size).tolist()
    else:
        bsk_network.vs["size"] = [size] * len(bsk_network.vs)

    # Label sizes
    if label_cex:
        max_deg = max(deg) if max(deg) > 0 else 1
        lsize = np.log(1 + (deg / max_deg)) * labelsize
        lsize[lsize < 0.5] = 0.5
        bsk_network.vs["label_size"] = lsize.tolist()
    else:
        bsk_network.vs["label_size"] = [labelsize] * len(bsk_network.vs)

    # Filter vertices based on degree or number
    if degree is not None:
        deg = np.array(bsk_network.degree())
        Deg = deg - np.diag(NetMatrix)
        Vind = Deg < degree
        if np.sum(~Vind) == 0:
            print("\ndegree argument is too high!\n\n")
            return None
        indices_to_delete = np.where(Vind)[0]
        bsk_network.delete_vertices(indices_to_delete)
        if bsk_S is not None:
            bsk_S.delete_vertices(indices_to_delete)
        # PATCH: recompute deg after filtering
        deg = np.array(bsk_network.degree())
        bsk_network.vs["deg"] = deg.tolist()

    elif n is not None:
        deg = np.array(bsk_network.degree())
        if n > len(deg):
            n = len(deg)
        nodes = np.argsort(deg)[-n:]
        indices_to_delete = np.setdiff1d(np.arange(len(deg)), nodes)
        bsk_network.delete_vertices(indices_to_delete)
        if bsk_S is not None:
            bsk_S.delete_vertices(indices_to_delete)
        # PATCH: recompute deg after filtering
        deg = np.array(bsk_network.degree())
        bsk_network.vs["deg"] = deg.tolist()

    # PATCH: check again after filtering
    if len(bsk_network.vs) == 0:
        return None

    # Simplify the graph
    if edges_min > 1:
        remove_multiple = False
    bsk_network.simplify(multiple=remove_multiple, loops=noloops)
    if bsk_S is not None:
        bsk_S.simplify(multiple=remove_multiple, loops=noloops)

    # Process edge weights
    if "weight" not in bsk_network.es.attributes():
        bsk_network.es["weight"] = [1] * len(bsk_network.es)
        bsk_network.es["width"] = [1] * len(bsk_network.es)

    if weighted:
        weights = np.array(bsk_network.es["weight"])
        if len(weights) > 0 and weights.max() != weights.min():
            normalized_weights = (weights - weights.min()) / (weights.max() - weights.min())
        else:
            normalized_weights = np.ones(len(weights))
        bsk_network.es["width"] = (normalized_weights * edgesize).tolist()
    else:
        if remove_multiple:
            bsk_network.es["width"] = [edgesize] * len(bsk_network.es)
        else:
            edges = np.array(bsk_network.es["weight"])
            max_edge = max(edges) if len(edges) > 0 and max(edges) > 0 else 1
            normalized_edges = edges / max_edge
            bsk_network.es["width"] = (normalized_edges * edgesize).tolist()

    # Remove edges below threshold
    if edges_min > 0:
        edges_to_remove = [e.index for e in bsk_network.es if e["weight"] < edges_min]
        bsk_network.delete_edges(edges_to_remove)
        if bsk_S is not None:
            bsk_S.delete_edges(edges_to_remove)

    # Remove isolated vertices if specified
    if remove_isolates:
        isolates = [v.index for v in bsk_network.vs if bsk_network.degree(v.index) == 0]
        bsk_network.delete_vertices(isolates)
        if bsk_S is not None:
            isolates_to_remove = [v.index for v in bsk_S.vs if v["name"] not in bsk_network.vs["name"]]
            bsk_S.delete_vertices(isolates_to_remove)
        # PATCH: recompute deg after removing isolates
        deg = np.array(bsk_network.degree())
        bsk_network.vs["deg"] = deg.tolist()

    # PATCH: check again after removing isolates
    if len(bsk_network.vs) == 0:
        return None

    # Apply clustering
    cl = clustering_network(bsk_network, cluster)
    bsk_network = cl["bsk_network"]

    if bsk_S is not None:
        bsk_S.vs["color"] = bsk_network.vs["color"]
        bsk_S.vs["community"] = bsk_network.vs["community"]
        bsk_S.vs["name"] = bsk_network.vs["name"]

    # Apply layout
    if bsk_S is not None:
        layout_results = switch_layout(bsk_S, type, community_repulsion)
        bsk_S = layout_results["bsk_network"]
    else:
        layout_results = switch_layout(bsk_network, type, community_repulsion)
        bsk_network = layout_results["bsk_network"]
    l = layout_results["l"]

    # Labeling the network
    LABEL = []
    if label:
        LABEL = list(bsk_network.vs["name"])
        if label_n is not None:
            # PATCH: safely get deg attribute
            deg_vals = bsk_network.vs["deg"] if "deg" in bsk_network.vs.attributes() else bsk_network.degree()
            q = 1 - (label_n / len(deg_vals)) if len(deg_vals) > 0 else 1
            if q <= 0:
                bsk_network.vs["label_size"] = [10] * len(bsk_network.vs)
            else:
                if q > 1:
                    q = 1
                q = np.quantile(deg_vals, q)
                for i, deg_val in enumerate(deg_vals):
                    if deg_val < q:
                        LABEL[i] = ""
                label_sizes = [10] * len(bsk_network.vs)
                for i, deg_val in enumerate(deg_vals):
                    if deg_val < q:
                        label_sizes[i] = 0
                bsk_network.vs["label_size"] = label_sizes

    if label_color:
        lab_color = bsk_network.vs["color"]
    else:
        lab_color = "black"

    # Setting Network Attributes
    bsk_network["alpha"] = alpha
    bsk_network["ylim"] = (-1, 1)
    bsk_network["xlim"] = (-1, 1)
    bsk_network["rescale"] = True
    bsk_network["asp"] = 0
    bsk_network["layout"] = l
    bsk_network["main"] = Title
    bsk_network.es["curved"] = [curved] * len(bsk_network.es)
    bsk_network.vs["label_dist"] = [0.7] * len(bsk_network.vs)
    bsk_network.vs["frame_color"] = adjust_color('black', alpha)
    bsk_network.vs["color"] = [adjust_color(c, alpha) for c in bsk_network.vs["color"]]
    bsk_network.vs["label_color"] = adjust_color('black', min(1, alpha + 0.1))
    bsk_network.vs["label_font"] = [2] * len(bsk_network.vs)
    bsk_network.vs["label"] = LABEL

    # Plot the network
    if halo and cluster != "none":
        if verbose:
            ig.plot(cl["net_groups"], bsk_network)
    else:
        bsk_network.es["color"] = [adjust_color(c, alpha / 2) for c in bsk_network.es["color"]]
        if verbose:
            ig.plot(bsk_network)

    # Output clustering results
    if cluster != "none":
        cluster_res = pd.DataFrame({
            "vertex": [v["name"] for v in bsk_network.vs],
            "cluster": [v["community"] for v in bsk_network.vs],
            "btw_centrality": bsk_network.betweenness(directed=False),
            "clos_centrality": bsk_network.closeness(),
            "pagerank_centrality": [x for x in bsk_network.pagerank()]
        })
        cluster_res = cluster_res.sort_values(by="cluster").reset_index(drop=True)
    else:
        cluster_res = None

    return {
        "S": S,
        "graph": bsk_network,
        "cluster_res": cluster_res,
        "cluster_obj": cl["net_groups"]
    }


def delete_isolates(graph, mode='all'):
    isolates = [v.index for v in graph.vs if graph.degree(v, mode=mode) == 0]
    graph.delete_vertices(isolates)
    return graph


def clustering_network(bsk_network, cluster):
    colorlist = color_list()

    # PATCH: wrap clustering in try/except — some algorithms fail on small or
    # disconnected graphs. Fall back to single-cluster assignment on failure.
    try:
        if cluster == "none":
            net_groups = type('FallbackClustering', (), {'membership': [0] * len(bsk_network.vs)})()
        elif cluster == "optimal":
            net_groups = bsk_network.community_optimal_modularity()
        elif cluster == "leiden":
            net_groups = bsk_network.community_leiden(objective_function="modularity", n_iterations=3, resolution_parameter=0.75)
        elif cluster == "louvain":
            net_groups = bsk_network.community_multilevel()
        elif cluster == "fast_greedy":
            net_groups = bsk_network.community_fastgreedy().as_clustering()
        elif cluster == "leading_eigen":
            net_groups = bsk_network.community_leading_eigenvector()
        elif cluster == "spinglass":
            net_groups = bsk_network.community_spinglass()
        elif cluster == "infomap":
            net_groups = bsk_network.community_infomap()
        elif cluster == "edge_betweenness":
            net_groups = bsk_network.community_edge_betweenness().as_clustering()
        elif cluster == "walktrap":
            net_groups = bsk_network.community_walktrap().as_clustering()
        else:
            print("\nUnknown cluster argument. Using default algorithm\n")
            net_groups = bsk_network.community_walktrap().as_clustering()
    except Exception as e:
        print(f"Clustering failed ({e}), falling back to single cluster.")
        net_groups = type('FallbackClustering', (), {'membership': [0] * len(bsk_network.vs)})()

    bsk_network.vs["community"] = net_groups.membership

    colorlist_hex = [rgba_to_hex(c) for c in colorlist]

    bsk_network.vs["color"] = [colorlist_hex[m % len(colorlist)] for m in net_groups.membership]
    el = np.array(bsk_network.get_edgelist())

    if len(el) > 0:
        bsk_network.es["color"] = [
            "#B3B3B3" if bsk_network.vs[el[i, 0]]["community"] != bsk_network.vs[el[i, 1]]["community"]
            else colorlist_hex[bsk_network.vs[el[i, 0]]["community"] % len(colorlist)]
            for i in range(len(el))
        ]
        bsk_network.es["lty"] = [5 if c == "#B3B3B3" else 1 for c in bsk_network.es["color"]]
    else:
        bsk_network.es["color"] = []
        bsk_network.es["lty"] = []

    return {"bsk_network": bsk_network, "net_groups": net_groups}


def switch_layout(bsk_network, type, community_repulsion):
    if community_repulsion > 0:
        community_repulsion = round(community_repulsion * 100)
        row = np.array(bsk_network.get_edgelist())
        membership = bsk_network.vs["community"]

        if len(row) > 0:
            if bsk_network.es["weight"] is None:
                bsk_network.es["weight"] = [
                    weight_community(row[i], membership, community_repulsion, 1)
                    for i in range(len(row))
                ]
            else:
                bsk_network.es["weight"] = [
                    bsk_network.es["weight"][i] + weight_community(row[i], membership, community_repulsion, 1)
                    for i in range(len(row))
                ]

    if type == "auto":
        l = bsk_network.layout_auto()
    elif type == "circle":
        l = bsk_network.layout_circle()
    elif type == "star":
        l = bsk_network.layout_star()
    elif type == "sphere":
        l = bsk_network.layout_sphere()
    elif type == "mds":
        l = bsk_network.layout_mds()
    elif type == "fruchterman":
        l = bsk_network.layout_fruchterman_reingold()
    elif type == "kamada":
        l = bsk_network.layout_kamada_kawai()
    else:
        l = bsk_network.layout_auto()

    # PATCH: avoid division by zero when all coordinates are identical
    l_coords = np.array(l.coords)
    min_coords = l_coords.min(axis=0)
    max_coords = l_coords.max(axis=0)
    range_coords = max_coords - min_coords
    range_coords[range_coords == 0] = 1
    normalized_coords = (l_coords - min_coords) / range_coords
    l = ig.Layout(normalized_coords.tolist())

    return {"l": l, "bsk_network": bsk_network}


def weight_community(row, membership, weight_within, weight_between):
    if membership[row[0]] == membership[row[1]]:
        return weight_within
    else:
        return weight_between


def adjust_color(color, alpha):
    return to_rgba(color, alpha)


def color_list():
    return [cm.tab20(i) for i in range(20)]


def normalize_similarity(NetMatrix, type="association"):
    D = np.diag(NetMatrix)
    if type == "association":
        S = NetMatrix / np.outer(D, D)
    elif type == "inclusion":
        S = NetMatrix / np.minimum.outer(D, D)
    elif type == "jaccard":
        S = NetMatrix / (np.outer(D, D) + NetMatrix - NetMatrix)
    elif type == "salton":
        S = NetMatrix / np.sqrt(np.outer(D, D))
    elif type == "equivalence":
        S = (NetMatrix / np.sqrt(np.outer(D, D))) ** 2
    else:
        raise ValueError(f"Unknown normalization type: {type}")
    
    S = np.nan_to_num(S)
    return S


def rgba_to_hex(rgba):
    r, g, b, a = rgba
    return '#{:02X}{:02X}{:02X}'.format(int(r * 255), int(g * 255), int(b * 255))