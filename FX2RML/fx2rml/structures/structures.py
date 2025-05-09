import hashlib

class InstanceMapping:
    def __init__(self, name, IRI=None):
        self.name = name
        self.IRI = IRI
        self.conditions = []
        self.datatype_properties = {}

    def set_conditions(self, conditions):
        self.conditions = conditions
    
    def add_datatype_property(self, property, column):
        self.datatype_properties[property] = column
    
    def set_datatype_properties(self, datatype_properties):
        self.datatype_properties = datatype_properties

    def __str__(self):
        return f"InstanceMapping(name={self.name}, datatype_properties={self.datatype_properties})"
    
    def get_key(self):
        return hashlib.md5(str(self).encode()).hexdigest()

class ListMapping:
    def __init__(self, name, IRI=None, is_collection=False):
        self.name = name
        self.IRI = IRI
        self.is_collection = is_collection
        self.conditions = []
        self.datatype_properties = {}
        self.instance_mappings = []

    def set_IRI(self, IRI):
        self.IRI = IRI

    def set_collectionIRI(self, collectionIRI):
        self.collectionIRI = collectionIRI

    def set_datatype_properties(self, datatype_properties):
        self.datatype_properties = datatype_properties

    def add_instance_mapping(self, instance_mapping):
        self.instance_mappings.append(instance_mapping)

    def get_instance_mappings(self):
        return self.instance_mappings

    def set_conditions(self, conditions):
        self.conditions = conditions
        for instance_mapping in self.instance_mappings:
            instance_mapping.set_conditions(conditions)

class ReferenceMapping:
    def __init__(self, predicate):
        self.predicate = predicate
        self.subject = None
        self.column = None
        self.target_value = None

    def set_subject(self, subject):
        self.subject = subject

    def set_column(self, column):
        self.column = column

    def set_target_value(self, target_value):
        self.target_value = target_value

class RelationMapping:
    def __init__(self, name):
        self.name = name
        self.predicate = name
        self.conditions = []

    def set_subject(self, subject):
        self.subject = subject

    def set_object(self, object):
        self.object = object
    
    def set_predicate(self, predicate):
       self.predicate = predicate
    
    def set_conditions(self, conditions):
        self.conditions = conditions