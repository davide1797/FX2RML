from structures.structures import *
from utils.utils import *

def count_tabs(line):
    """
    Count the number of tabs in a line.

    Args:
        line : String representing a line of text.

    Returns:
        int: Number of leading tabs in the line.
    """
    return len(line) - len(line.lstrip('\t'))       # calculate the number of tabs in the line

def parse_lines(lines):     # create tree structure from the tabs
    """
    Create a tree structure from lines based on indentation.

    Args:
        lines : List of strings representing lines of text.

    Returns:
        list: Tree structure as a list of nested dictionaries.
    """
    stack = []
    tree = []
    current_level = -1

    for line in lines:
        line = line.rstrip()
        if not line: continue

        indent = count_tabs(line)
        content = line.lstrip('\t')

        node = {"line": content, "children": []}

        if indent > current_level:
            if stack:
                stack[-1]["children"].append(node)
            else:
                tree.append(node)
            stack.append(node)
            current_level = indent
        else:
            while len(stack) > indent:
                stack.pop()
            if stack:
                stack[-1]["children"].append(node)
            else:
                tree.append(node)
            stack.append(node)
            current_level = indent

    return tree

def print_tree(nodes, level=0):
    """
    Print a tree structure.

    Args:
        nodes : List of tree nodes.
        level : Current indentation level (default is 0).

    Returns:
        None
    """
    for node in nodes:
        print("    " * level + node["line"])
        print_tree(node["children"], level + 1)

def get_fx2rml_prefixes(nodes, separator):            # find the prefixes in FX2RML
    """
    Extract prefixes and graph name from FX2RML nodes.

    Args:
        nodes : List of tree nodes.
        separator : Separator used in the prefixes.

    Returns:
        tuple: Graph name and dictionary of prefixes.
    """
    prefixes = {}
    graph_name = ""
    for node in nodes:
        prefix = node["line"].replace(" ", "")
        if prefix.split(separator)[1] == "this":        # = this in prefixes
            graph_name = prefix.split(separator)[0]
        else:
            abbreviation = prefix.split(separator)[0]
            prefix = prefix.split(separator)[1]
            prefixes[abbreviation] = prefix

    return graph_name, prefixes

def get_children(nodes, node_name):
    """
    Get the children of a node by name.

    Args:
        nodes : List of tree nodes.
        node_name : Name of the node to search for.

    Returns:
        list: Children of the matching node or None if not found.
    """
    for node in nodes:
        if node_name in node["line"]:
            return node["children"]
        
    return None

def get_conditions(prefix_mappings, nodes):                     # find the class conditions in FX2RML
    """
    Extract conditions for a class from FX2RML nodes.

    Args:
        prefix_mappings : Dictionary of prefix mappings.
        nodes : List of tree nodes.

    Returns:
        list: List of conditions as tuples.
    """
    conditions = []
    for node in nodes:
        value = node["line"]
        if "$" in value:
            if "." not in value:           # condition on atomic value
                column = "$" + value.split("$")[1].split("]")[0] + "]"
            else:                           # condition on nested value
                column = "$" + value.split("$")[1].split("]")[0] + "]" + "." + value.split("].")[1].split(" ")[0]
            if "==" in value:
                operator = "=="
            elif "<=" in value:
                operator = "<="
            elif ">=" in value:
                operator = ">="
            elif "<" in value:
                operator = "<"
            elif ">" in value:
                operator = ">"
            elif "!=" in value:
                operator = "!="
            label = value.split(operator)[1].split("\"")[1].split("\"")[0]
            full_class_name = get_full_name(value, prefix_mappings, " ")
            condition = (column, operator, label, full_class_name)              # structure of conditions
        else:           #default condition
            full_class_name = get_full_name(value, prefix_mappings, " ")
            condition = ("", "", "", full_class_name)              # default condition
        conditions.append(condition)

    return conditions

def get_datatype_properties(prefix_mappings, nodes, separator):             # find the datatype properties in FX2RML
    """
    Extract datatype properties from FX2RML nodes.

    Args:
        prefix_mappings : Dictionary of prefix mappings.
        nodes : List of tree nodes.
        separator : Separator used in the properties.

    Returns:
        dict: Dictionary of datatype properties.
    """
    datatype_properties = {}
    for node in nodes:
        value = node["line"]
        if "class" not in value:                                # if it is not the "class" tag
            if value == "collection":
                datatype_properties["collection"] = ""          # flag for collection
            else:
                full_datatype_property = get_full_name(value, prefix_mappings, separator)       # get full datatype property
                column = "$" + node["line"].split("$")[1]
                datatype_properties[full_datatype_property] = column

    return datatype_properties

def get_fx2rml_instances(prefix_mappings, nodes, separator):
    """
    Extract instances and lists from FX2RML nodes.

    Args:
        prefix_mappings : Dictionary of prefix mappings.
        nodes : List of tree nodes.
        separator : Separator used in the properties.

    Returns:
        tuple: List of instance mappings and list mappings.
    """
    instance_mappings = []
    list_mappings = []
    for node in nodes:
        IRI = None
        if "[" not in node["line"]:                 # if it is not a list
            if "/" in node["line"]:                 # if it is not a "row" mapping
                prefix = node["line"].split("/")[0]
                class_name = prefix_mappings[prefix] + "/" + node["line"].split("/")[1] 
                conditions = [("", "", "", class_name)]     # fixed condition
            else:                                   # class choice
                class_children = get_children(node["children"], "class")           # find "class" tag
                conditions = get_conditions(prefix_mappings, class_children)
            datatype_properties = get_datatype_properties(prefix_mappings, node["children"], separator)
            IRI = datatype_properties["IRI"] if "IRI" in datatype_properties else None              # see if IRI is specified in instance
            im = InstanceMapping(node["line"], IRI)
            im.set_conditions(conditions)
            im.set_datatype_properties(datatype_properties)
            instance_mappings.append(im)
        else:                   # if it is a list
            cleaned_node = node["line"].replace("[", "").replace("]", "")       # remove [ and ]
            if "/" in node["line"]:             
                prefix = cleaned_node.split("/")[0]
                class_name = prefix_mappings[prefix] + "/" + cleaned_node.split("/")[1] 
                conditions = [("", "", "", class_name)]
            else:
                class_children = get_children(node["children"], "class")
                conditions = get_conditions(prefix_mappings, class_children)
            
            datatype_properties = get_datatype_properties(prefix_mappings, node["children"], separator)
            IRI = datatype_properties["IRI"] if "IRI" in datatype_properties else None              # see if IRI is specified in list
            is_collection = "collection" in datatype_properties              # see if IRI is specified in list
            lm = ListMapping(cleaned_node, IRI, is_collection)
            lm.set_conditions(conditions)
            lm.set_datatype_properties(datatype_properties)
            list_mappings.append(lm)
    
    return instance_mappings, list_mappings

def get_fx2rml_references(prefix_mappings, nodes, separator): 
    """
    Extract references from FX2RML nodes.

    Args:
        prefix_mappings : Dictionary of prefix mappings.
        nodes : List of tree nodes.
        separator : Separator used in the properties.

    Returns:
        list: List of reference mappings.
    """    
    refernces_mappings = []
    for node in nodes:
        full_object_property = get_full_name(node["line"], prefix_mappings)     # get full object property
        for child in node["children"]:
            if "subject" in child["line"]:       # column
                subject = child["line"].split(separator)[1].replace(" ", "")
            elif "condition" in child["line"]:       # target_value
                column = child["line"].split(separator)[1].split("==")[0].replace(" ", "")
                target_value = child["line"].split("==")[1].replace(" ", "")
        rm = ReferenceMapping(full_object_property)
        rm.set_subject(subject)
        rm.set_column(column)
        rm.set_target_value(target_value)
        refernces_mappings.append(rm)

    return refernces_mappings

def in_mapping(mappings, name):             # verify that a name used as subject or object exist in the FX2RML file
    """
    Check if a name exists in the instance mappings.

    Args:
        mappings : List of mappings.
        name : Name to check.

    Returns:
        bool: True if the name exists, False otherwise.
    """
    for mapping in mappings:
        if mapping.name == name:
            return True
        
    return False 

def get_fx2rml_relations(prefixes_mappings, instances_mappings, lists_mappings, nodes):    
    """
    Extract relations from FX2RML nodes.

    Args:
        prefixes_mappings : Dictionary of prefix mappings.
        instances_mappings : List of instance mappings.
        lists_mappings : List of list mappings.
        nodes : List of tree nodes.

    Returns:
        list: List of relation mappings.
    """  
    relation_mappings = []
    for node in nodes:      # for every relation
        full_object_property = get_full_name(node["line"], prefixes_mappings)     # get full object property
        for child in node["children"]:
            value = child["line"].split("=")[1].replace(" ", "")
            is_list = ""
            predicate = None
            conditions = None
            if "[" in value:        # if value is a list
                is_list = "_"
                value = value.replace("[", "").replace("]", "")
            if "subject" in child["line"] and (in_mapping(instances_mappings, value) or in_mapping(lists_mappings, value)):       # subject
                subject = value + is_list           # add _ if it is a list
            elif "predicate" in child["line"]:       # predicate
                if "/" in node["line"]:             # single predicate value
                    predicate = value 
                    conditions = [("", "", "", get_full_name(predicate))]        # default condition
                else:
                    predicate_children = get_children(node["children"], "predicate")           # find "predicate" tag
                    conditions = get_conditions(prefixes_mappings, predicate_children)   
            elif "object" in child["line"] and (in_mapping(instances_mappings, value) or in_mapping(lists_mappings, value)):      # object
                object = value + is_list
        if predicate is None and conditions is None:        # if predicate is not specified, use the object property name
            predicate = full_object_property
            conditions = [("", "", "", full_object_property)]        # default condition
        rm = RelationMapping(full_object_property)          # predicate unnecessary given the name
        rm.set_subject(subject)
        rm.set_predicate(predicate)
        rm.set_object(object)
        rm.set_conditions(conditions)
        relation_mappings.append(rm)

    return relation_mappings

def get_mapping(mapping_file, separator="="):
    """
    Parse an FX2RML mapping file and extract its components.

    Args:
        mapping_file : Path to the FX2RML mapping file.
        separator : Separator used in the file (default is "=").

    Returns:
        tuple: Graph name, prefixes, instances, lists, references, and relations.
    """
    references_mappings = []
    relations_mappings = []
    with open(mapping_file, 'r') as file:
        lines = file.readlines()
        tree = parse_lines(lines)
    for node in tree:               # top level nodes
        if node["line"] == "prefixes":
            graph_name, prefixes_mappings = get_fx2rml_prefixes(node["children"], separator)
        elif node["line"] == "instances":
            instances_mappings, lists_mappings = get_fx2rml_instances(prefixes_mappings, node["children"], separator)
        elif node["line"] == "references":
            references_mappings = get_fx2rml_references(prefixes_mappings, node["children"], separator)
        elif node["line"] == "relations":
            relations_mappings = get_fx2rml_relations(prefixes_mappings, instances_mappings, lists_mappings, node["children"])
    
    return graph_name, prefixes_mappings, instances_mappings, lists_mappings, references_mappings, relations_mappings