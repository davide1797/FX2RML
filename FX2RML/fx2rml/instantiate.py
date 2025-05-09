from structures.structures import *
from utils.utils import *

def instantiate_value(mapping, row_data):
    """
    Instantiate a value from a mapping and row data.

    Args:
        mapping : Mapping string containing column references.
        row_data : Dictionary of row data.

    Returns:
        str: Instantiated value or None if the column is not found.
    """
    col = mapping.split("$[")[1].split("]")[0].replace("\"", "") 
    if col not in row_data:
        return None  
    if row_data[col].endswith(".0"):
        row_data[col] = row_data[col].split(".0")[0]
    mapping = str(row_data[col]) + mapping.split("]")[1]
    
    return mapping

def instantiate_list(list_mapping, row_data):
    """
    Instantiate a list from a list mapping and row data.

    Args:
        list_mapping : List mapping object.
        row_data : Dictionary of row data.

    Returns:
        list: Instantiated list.
    """
    col = ""
    for _, value in list_mapping.datatype_properties.items():
        col = value.split("$[")[1].split("]")[0].replace("\"", "")
        break
    return row_data[col]

def instantiate_subvalue(field, json_data):
    """
    Instantiate a subvalue from a field and JSON data.

    Args:
        field : Field string containing subfield references.
        json_data : JSON data dictionary.

    Returns:
        str: Instantiated subvalue or None if the subfield is not found.
    """
    if "^^" not in field:
        subfield = field.split("].")[1] 
        if subfield not in json_data:
            return None
        return str(json_data[subfield])
    
    subfield = field.split("].")[1].split("^^")[0]
    value_type = field.split("^^")[1]

    if subfield not in json_data:
        return None
    
    return str(json_data[subfield]) + "^^" + value_type

def instantiate_instances(instances_mapping, lists_mappings, row_data):
    """
    Instantiate instances and lists from mappings and row data.

    Args:
        instances_mapping : List of instance mappings.
        lists_mappings : List of list mappings.
        row_data : Dictionary of row data.

    Returns:
        tuple: List of instantiated instances and lists.
    """
    instances = []
    lists = []
    for instance_mapping in instances_mapping:                          # simple instances
        if instance_mapping.IRI is not None and "$" in instance_mapping.IRI:        # if IRI is specified as a column
            IRI = instantiate_value(instance_mapping.IRI, row_data)        # instantiate the IRI
        else:  
            IRI = None
        im = InstanceMapping(instance_mapping.name, IRI)        # create instance mapping with substitutions
        for property, value in instance_mapping.datatype_properties.items():
            if value is not None and "$" in value:                # if the value is specified as a column
                cell_value = instantiate_value(value, row_data)
                if cell_value is not None:
                    im.datatype_properties[property] = cell_value         # instantiate the value
            else:
                im.datatype_properties[property] = instance_mapping.datatype_properties[property]        # keep the original value
        conditions = []         #new conditions
        for condition in instance_mapping.conditions:
            if value is not None and "$" in condition[0]:                # if the column is specified as a column
                conditions.append((instantiate_value(condition[0], row_data), condition[1], condition[2], condition[3]))        # instantiate the value for triggering the condition
            else:
                conditions.append(condition)            # keep the original condition
        im.set_conditions(conditions)        # update the conditions
        instances.append(im)        # add the instance mapping to the list

    for list_mapping in lists_mappings:        # list instances   
        lm = ListMapping(list_mapping.name + "_", list_mapping.IRI, list_mapping.is_collection)        # create list mapping with substitutions
        json_data = instantiate_list(list_mapping, row_data)        # instantiate the list
        for i in range(0, len(json_data)):
            if list_mapping.IRI is not None and "$" in list_mapping.IRI:        # if IRI is specified as a column
                local_IRI = instantiate_subvalue(lm.IRI, json_data[i])
                IRI = local_IRI
            else:
                IRI = None
            im = InstanceMapping(lm.name + str(i), IRI)
            for property, value in list_mapping.datatype_properties.items():
                if property != "IRI" and property != "collection":        # if it is not the IRI or collection property
                    if value is not None and "$" in value:                # if the value is specified as a column
                        cell_value = instantiate_subvalue(value, json_data[i])
                        if cell_value is not None:
                            im.datatype_properties[property] = cell_value         # instantiate the value
                    else:
                        im.datatype_properties[property] = instance_mapping.datatype_properties[property]        # keep the original value
            conditions = []         #new conditions
            for condition in list_mapping.conditions:
                if value is not None and "$" in condition[0]:                # if the column is specified as a column
                    conditions.append((instantiate_subvalue(condition[0], json_data[i]), condition[1], condition[2], condition[3]))        # instantiate the value for triggering the condition
                else:
                    conditions.append(condition)            # keep the original condition
            im.set_conditions(conditions)       # non parametric for lists
            lm.add_instance_mapping(im)        # add the instance mapping to the list
            instances.append(im)        # add the instance mapping to the list
        
        lists.append(lm)        # add the instance mapping to the list
    
    return instances, lists

def instantiate_references(prefixes_mappings, references_mappings, row_data):
    """
    Instantiate references from mappings and row data.

    Args:
        prefixes_mappings : Dictionary of prefix mappings.
        references_mappings : List of reference mappings.
        row_data : Dictionary of row data.

    Returns:
        list: List of instantiated references.
    """
    references = []
    for reference_mapping in references_mappings:        # for every reference mapping
        target_value = instantiate_value(reference_mapping.target_value, row_data)
        if target_value is not None:        # if the value is specified as a column
            rm = ReferenceMapping(reference_mapping.predicate)        # create reference mapping with substitutions
            rm.set_subject(reference_mapping.subject)
            full_property = reference_mapping.column.split(".")[0] + "." + reference_mapping.column.split(".")[1] + "." + get_full_name(reference_mapping.column.split(".")[2], prefixes_mappings)
            rm.set_column(full_property)
            rm.set_target_value(target_value)
            references.append(rm)        # add the instance mapping to the list

    return references

def instantiate_relations(relations_mappings, row_data):
    """
    Instantiate relations from mappings and row data.

    Args:
        relations_mappings : List of relation mappings.
        row_data : Dictionary of row data.

    Returns:
        list: List of instantiated relations.
    """
    relations = []
    for relation_mapping in relations_mappings:     
        predicate = None                    
        rm = RelationMapping(relation_mapping.name)        # create relation mapping with substitutions
        if relation_mapping.predicate is None:        # if predicate is not specified
            conditions = []         #new conditions
            for condition in relation_mapping.conditions:
                if "$" in condition[0]:                # if the column is specified as a column
                    conditions.append((instantiate_value(condition[0], row_data), condition[1], condition[2], condition[3]))        # instantiate the value for triggering the condition
                else:
                    conditions.append(condition)            # keep the original condition
            rm.set_conditions(conditions)        # update the conditions
        else:
            predicate = relation_mapping.predicate
        rm.set_predicate(predicate)        # update the predicate
        rm.set_subject(relation_mapping.subject)
        rm.set_object(relation_mapping.object)
        
        relations.append(rm)        # add the instance mapping to the list
    
    return relations