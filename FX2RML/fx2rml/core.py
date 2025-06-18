#!/usr/bin/env python3
from rdflib import Graph, RDF, URIRef, Literal, BNode
from rdflib.collection import Collection
import pandas as pd
import ast
import re
import argparse
from structures.structures import *
from utils.utils import *
from parsing.parser import *
from instantiate import *
import os

def json_value_of(json_data, key):
    """
    Get json value by key.

    Args:
        json_data : JSON piece.
        key : Key to search in the JSON data.

    Returns:
        str: value for the JSON key.
    """
    if json_data is not [] and key in json_data:
        return json_data[key]
    else:
        return ""           

def add_target_values(graph_name, instance_mapping, IRI, target_values):
    """
    Add target values to the graph mapping.

    Args:
        graph_name : Name of the graph.
        instance_mapping : Instance mapping object.
        IRI : IRI of the instance.
        target_values : Dictionary of target values.

    Returns:
        dict: Updated target values.
    """
    if graph_name in target_values and instance_mapping.name in target_values[graph_name]:        # if the instance mapping is in the target values
        for property, _ in target_values[graph_name][instance_mapping.name].items():
            if property in instance_mapping.datatype_properties.keys():
                property_value = instance_mapping.datatype_properties[property].split("^^")[0] if "^^" in instance_mapping.datatype_properties[property] else instance_mapping.datatype_properties[property] 
                if property_value in target_values[graph_name][instance_mapping.name][property]:
                    IRIs = target_values[graph_name][instance_mapping.name][property][property_value]
                    IRIs.append(IRI)
                    target_values[graph_name][instance_mapping.name][property][property_value] = IRIs
                else:
                    target_values[graph_name][instance_mapping.name][property][property_value] = [IRI]
    return target_values

def add_collections(g, lists_mappings, mapped_instances):
    """
    Add collections to the RDF graph.

    Args:
        g : RDF graph.
        lists_mappings : List of list mappings.
        mapped_instances : Dictionary of mapped instances.

    Returns:
        dict: Dictionary of collections.
    """
    collections = {}
    for list_mapping in lists_mappings:        # for every list mapping
        if list_mapping.is_collection:        # if it is a collection
            individuals = []
            head_bnode = BNode()
            for im in list_mapping.get_instance_mappings():        # for every instance mapping in the list
                individuals.append(URIRef(mapped_instances[im.name]))
            if len(individuals) > 0:
                Collection(g, head_bnode, individuals)
                collections[list_mapping.name] = head_bnode
    return collections

def add_instances(graph_name, g, counters, mapped_iris, mapped_instances, instances_mapping, lists_mappings, references, references_table, target_values):
    """
    Add instances to the RDF graph.

    Args:
        graph_name : Name of the graph.
        g : RDF graph.
        counters : Dictionary of counters for IRIs.
        mapped_iris : Dictionary of mapped IRIs.
        mapped_instances : Dictionary of mapped instances.
        instances_mapping : List of instance mappings.
        lists_mappings : List of list mappings.
        references : List of references.
        references_table : List of references table.
        target_values : Dictionary of target values.

    Returns:
        tuple: Updated graph, references table, target values, counters, mapped IRIs, mapped instances, and collections.
    """
    for instance_mapping in instances_mapping:  #for every individual that needs to be created
        label = get_correct_label(instance_mapping)        # find the satisfied condition to determine the class
        IRI = instance_mapping.IRI
        if instance_mapping.IRI is None:        # if IRI is None, create a new one
            if instance_mapping.name not in mapped_iris:
                if label not in counters:
                    counters[label] = 0
                else:
                    counters[label] += 1
                IRI = label + "_" + str(counters[label])        # create a new IRI
                key = instance_mapping.get_key()        # create hash key
                dictionary = {}        # create internal dictionary
                dictionary[key] = IRI        # update internal dictionary
                mapped_iris[instance_mapping.name] = dictionary            # update external dictionary
            else:
                dictionary = mapped_iris[instance_mapping.name]     # get internal dictionary
                if instance_mapping.get_key() in dictionary:
                    IRI = dictionary[instance_mapping.get_key()]    #fetch existing IRI
                else:
                    if label not in counters:
                        counters[label] = 0
                    else:
                        counters[label] += 1
                    IRI = label + "_" + str(counters[label])        # create a new IRI
                    key = instance_mapping.get_key()        # create hash key
                    dictionary[key] = IRI        # update internal dictionary
                    mapped_iris[instance_mapping.name] = dictionary            # update external dictionary
            
        # add the instance to the graph
        individual = URIRef(IRI)
        g.add((individual, RDF.type, URIRef(label)))
        mapped_instances[instance_mapping.name] = individual

        # add datatype properties
        for property, value in instance_mapping.datatype_properties.items():
            g.add((individual, URIRef(property), Literal(value)))

        # update target values
        target_values = add_target_values(graph_name, instance_mapping, IRI, target_values)        # add the instance mapping to the target values

    collections = add_collections(g, lists_mappings, mapped_instances)        # add collections to the graph

    # add references in table
    for reference in references:
        if reference.column is not None:
            subjectIRI = mapped_instances[reference.subject]
            predicate = reference.predicate
            column = reference.column
            target_value = reference.target_value
            references_table.append((subjectIRI, predicate, column, target_value))

    return g, references_table, target_values, counters, mapped_iris, mapped_instances, collections

def add_references(g, references_table, target_values):
    """
    Add references to the RDF graph.

    Args:
        g : RDF graph.
        references_table : List of references table.
        target_values : Dictionary of target values.

    Returns:
        Graph: Updated RDF graph.
    """
    for reference in references_table:
        subjectIRI = reference[0]
        predicate = reference[1]
        graph = reference[2].split(".")[0]
        instance_mapping = reference[2].split(".")[1]
        column = reference[2].split(".")[2]
        target_value = reference[3]
        if graph in target_values and instance_mapping in target_values[graph] and column in target_values[graph][instance_mapping] and target_value in target_values[graph][instance_mapping][column]:
            objectIRIs = target_values[graph][instance_mapping][column][target_value]
            for IRI in objectIRIs:
                g.add((subjectIRI, URIRef(predicate), URIRef(IRI)))

    return g

def add_relations(g, mapped_instances, collections, relations_mapping):
    """
    Add relations to the RDF graph.

    Args:
        g : RDF graph.
        mapped_instances : Dictionary of mapped instances.
        collections : Dictionary of collections.
        relations_mapping : List of relations mappings.

    Returns:
        Graph: Updated RDF graph.
    """
    for relation in relations_mapping:
        label = get_correct_label(relation)        # find the satisfied condition to determine the label
        for subject in get_IRI_dictionary(mapped_instances, relation.subject, collections):
            for object in get_IRI_dictionary(mapped_instances, relation.object, collections):
                subj_node = URIRef(subject) if not isinstance(subject, BNode) else subject
                obj_node = URIRef(object) if not isinstance(object, BNode) else object
                g.add((subj_node, URIRef(label), obj_node))
    return g

#def add_list_mapping(g, counters, mapped_iris, mapped_instances, list_mappings):
    # for every list mapping, create its instances
#    for list_mapping in list_mappings:
#        g, counters, target_values, mapped_iris, mapped_instances = add_instances(g, counters, mapped_iris, mapped_instances, list_mapping.get_instance_mappings())
    
#    return g, counters, mapped_iris, mapped_instances   

def get_IRI_dictionary(dict, key, collections):
    """
    Get IRIs for a given key in the list of instances.

    Args:
        dict : Dictionary of mapped instances.
        key : Key to search in the dictionary.
        collections : Dictionary of collections.

    Returns:
        list: List of IRIs or collections.
    """
    if key in collections:
        return [collections[key]]
    if "_" in key:      #if it is a list mapping
        
        pattern = re.compile(rf'^{key}')        # regular expression to match keys starting with key_

        filtered_dict = {k: v for k, v in dict.items() if pattern.match(k)}     # filter dictionary keys using the regular expression
        return list(filtered_dict.values())
    else:
        return [dict[key]] if key in dict else []

def update_target_values(prefixes_mappings, references_mappings, target_values):
    """
    Update target values from references mappings.

    Args:
        prefixes_mappings : Dictionary of prefixes mappings.
        references_mappings : List of references mappings.
        target_values : Dictionary of target values.

    Returns:
        dict: Updated target values.
    """
    for reference_mapping in references_mappings:                   # for all the references
        graph_name = reference_mapping.column.split(".")[0]
        instance_mapping = reference_mapping.column.split(".")[1]
        property = get_full_name(reference_mapping.column.split(".")[2], prefixes_mappings)
        if graph_name not in target_values:         # if the graph is not present yet
            target_values[graph_name] = {}
        if instance_mapping not in target_values[graph_name]:           # if the instance_mapping is not present yet
            property_dict = {}
            property_dict[property] = {}
            target_values[graph_name][instance_mapping] = property_dict
        elif property not in target_values[graph_name][instance_mapping]:       # if the property is not present yet
            property_dict = target_values[graph_name][instance_mapping]
            property_dict[property] = {}
            target_values[graph_name][instance_mapping] = property_dict

    return target_values

def get_column_list(datatype_properties):
    """
    Get the column associated with a datatype properties.

    Args:
        datatype_properties : Dictionary of datatype properties.

    Returns:
        str: Column name.
    """
    col = None
    for _, value in datatype_properties.items():
        if "$" in value:
            col = value.split("\"")[1].split("\"")[0] 
            break
    return col

def safe_literal_eval(val):
    """
    Safely evaluate a string literal.

    Args:
        val : String value to evaluate.

    Returns:
        object: Evaluated value or empty list on failure.
    """
    try:
        return ast.literal_eval(val)
    except (ValueError, SyntaxError):
        return []  
    
def clean_data_frame(tabular_file, lists_mappings):
    """
    Clean and format the tabular data frame.

    Args:
        tabular_file : Path to the tabular file.
        lists_mappings : List of list mappings.

    Returns:
        DataFrame: Cleaned data frame.
    """
    list_columns = []
    for list in lists_mappings:
        col = get_column_list(list.datatype_properties)
        list_columns.append(col)
       
    dirty_frame = pd.read_csv(tabular_file, sep=",", header=0)

    data_frame = pd.DataFrame()  # cleaned DataFrame

    for col in dirty_frame.columns:
        if col in list_columns:
            data_frame[col] = dirty_frame[col].astype('object').apply(lambda x: safe_literal_eval(x) if isinstance(x, str) else "")
        else:
            data_frame[col] = dirty_frame[col].apply(lambda x: str(x) if pd.notna(x) else "")        # convert to string and replace NaN with empty string

    return data_frame

def get_columns_value(row):
    """
    Get non-empty column values from a row.

    Args:
        row : Row of the data frame.

    Returns:
        dict: Dictionary of column values.
    """
    columns = {}
    for key, value in row.items():
        if value != "":
            columns[key] =  value
    return columns

def fx2rml(here, mapping_files, tabular_files, output_file, output_format="ttl"):
    """
    Execute FX2RML mappings on tabular data.

    Args:
        mapping_files : List of mapping files.
        tabular_files : List of tabular files.
        output_file : Path to the output file.
        output_format : Format of the output file (default: "ttl").

    Returns:
        Graph: RDF graph.
    """
    target_values = {}
    references_table = []

    source_index = 0
    g = Graph()

    for source_index in range(0, len(mapping_files)):
        mapping_file = here + "/" + mapping_files[source_index]
        tabular_file = here + "/" + tabular_files[source_index]
        graph_name, prefixes_mappings, instances_mappings, lists_mappings, references_mappings, relations_mappings = get_mapping(mapping_file)
        target_values = update_target_values(prefixes_mappings, references_mappings, target_values)
    
    for source_index in range(0, len(mapping_files)):
        mapping_file = here + "/" + mapping_files[source_index]
        tabular_file = here + "/" + tabular_files[source_index]

        graph_name, prefixes_mappings, instances_mappings, lists_mappings, references_mappings, relations_mappings = get_mapping(mapping_file)     
        data_frame = clean_data_frame(tabular_file, lists_mappings)        # clean the data frame
        counters = {}       # counters for mappings with unspecified IRIs
        mapped_instances = {}       # list of mapped instances (for instance mapping)
        mapped_iris = {}       # list of mapped IRIs (for reusing)
        for _, row in data_frame.iterrows():
            columns = get_columns_value(row)        # get the columns values
            instances, lists = instantiate_instances(instances_mappings, lists_mappings, columns)        # substitute the values in the mapping
            references = instantiate_references(prefixes_mappings, references_mappings, columns)
            relations = instantiate_relations(relations_mappings, columns)  
               
            # add instances
            g, references_table, target_values, counters, mapped_iris, mapped_instances, collections = add_instances(graph_name, g, counters, mapped_iris, mapped_instances, instances, lists, references, references_table, target_values)
            
            #g, counters, mapped_iris, mapped_instances = add_list_mapping(g, counters, mapped_iris, mapped_instances, list_mappings)
            
            g = add_relations(g, mapped_instances, collections, relations)   # add object properties        

    g = add_references(g, references_table, target_values)   # add references
    
    g.serialize(here + "/" + output_file, output_format)
    
    return g

def main():
    parser = argparse.ArgumentParser(description="Run FX2RML mappings on tabular data.")
    here = os.getcwd()

    parser.add_argument(
        "--mappings", 
        nargs="+", 
        required=True, 
        help="One or more FX2RML mapping (.fxrml) files"
    )

    parser.add_argument(
        "--inputs", 
        nargs="+", 
        required=True, 
        help="One or more tabular (.csv) files"
    )

    parser.add_argument(
        "--output", 
        required=True, 
        help="Path to output file"
    )

    args = parser.parse_args()
    output_format = args.output.split(".")[-1] 
    
    g = fx2rml(here, args.mappings, args.inputs, args.output, output_format)     # Call FX2RML function with parsed arguments
    #print_graph(g)

"""
def mymain():
    mapping_files = ["/home/depierro/Desktop/INRAe/ISWC 2025/FX2RML/tests/Suicides Rates/suicides rates.fxrml"]    
    tabular_files = ["/home/depierro/Desktop/INRAe/ISWC 2025/FX2RML/tests/Suicides Rates/suicides rates.csv"]
    output_file = "/home/depierro/Desktop/INRAe/ISWC 2025/FX2RML/tests/Suicides Rates/suicides rates.ttl"

    mapping_files = ["/home/depierro/Desktop/INRAe/ISWC 2025/FX2RML/tests/Electric Vehicles/electric vehicles.fxrml"]    
    tabular_files = ["/home/depierro/Desktop/INRAe/ISWC 2025/FX2RML/tests/Electric Vehicles/ec.csv"]
    output_file = "/home/depierro/Desktop/INRAe/ISWC 2025/FX2RML/tests/Electric Vehicles/electric vehicles_1.ttl"

    mapping_files = ["/home/depierro/Desktop/INRAe/ISWC 2025/FX2RML/tests/PFAS/pfas.fxrml", "/home/depierro/Desktop/INRAe/ISWC 2025/FX2RML/tests/PFAS/matrix.fxrml"]    
    tabular_files = ["/home/depierro/Desktop/INRAe/ISWC 2025/FX2RML/tests/PFAS/pfas_2.csv", "/home/depierro/Desktop/INRAe/ISWC 2025/FX2RML/tests/PFAS/matrix.csv"]
    output_file = "/home/depierro/Desktop/INRAe/ISWC 2025/FX2RML/tests/PFAS/pfas_1.ttl"

    g = fx2rml(mapping_files, tabular_files, output_file)
    
    #print_graph(g)
"""

if __name__ == "__main__":
    main()
    #mymain()
