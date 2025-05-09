def get_full_name(value, prefix_mappings, separator="="):           # distinguish whether there is an abbreviation or not in FX2RML
    """
    Get the full name of a value by resolving its prefix.

    Args:
        value : String containing the value to resolve.
        prefix_mappings : Dictionary of prefix mappings.
        separator : Separator used in the value (default is "=").

    Returns:
        str: Full name of the value or "IRI" if the value contains "IRI".
    """
    if "IRI" not in value:
        prefix = value.split("/")[0]
        if prefix in prefix_mappings:
            prefix = prefix_mappings[prefix]
            rest = value.split("/")[1].split(separator)[0].replace(" ", "")
            full_name = prefix + "/" + rest
        else:
            full_name = value.split(" ")[0]
    else:
        full_name = "IRI"

    return full_name

def get_correct_label(mapping):
    """
    Get the correct label for a mapping based on its conditions.

    Args:
        mapping : Mapping object containing conditions.

    Returns:
        str: Label determined by the first satisfied condition.
    """
    correct_condition = False
    i = 0
    label = ""
    while not correct_condition and i < len(mapping.conditions):            # find the satisfied condition to determine the class/predicate label
        if mapping.conditions[i][1] == "==" and str(mapping.conditions[i][0]) == mapping.conditions[i][2]:          # == operator
            correct_condition = True
            label = mapping.conditions[i][3]
        elif mapping.conditions[i][1] == "<" and str(mapping.conditions[i][0]) < mapping.conditions[i][2]:          # < operator
            correct_condition = True
            label = mapping.conditions[i][3]
        elif mapping.conditions[i][1] == "<=" and str(mapping.conditions[i][0]) <= mapping.conditions[i][2]:        # <= operator
            correct_condition = True
            label = mapping.conditions[i][3]
        elif mapping.conditions[i][1] == ">" and str(mapping.conditions[i][0]) > mapping.conditions[i][2]:          # > operator
            correct_condition = True
            label = mapping.conditions[i][3]
        elif mapping.conditions[i][1] == ">=" and str(mapping.conditions[i][0]) >= mapping.conditions[i][2]:        # >= operator
            correct_condition = True
        elif mapping.conditions[i][1] == "!=" and str(mapping.conditions[i][0]) != mapping.conditions[i][2]:        # != operator
            correct_condition = True
            label = mapping.conditions[i][3]
        elif mapping.conditions[i][1] == "":        # default condition
            correct_condition = True              
            label = mapping.conditions[i][3]
        i += 1
    
    return label

def print_graph(g):
    """
    Print the first 10 triples in an RDF graph.

    Args:
        g : RDF graph to print.

    Returns:
        None
    """
    i = 0
    for subj, pred, obj in g:
        print(f"Subject: {subj}")
        print(f"Predicate: {pred}")
        print(f"Object: {obj}")
        print("---")
        i += 1
        if i > 10:
            break