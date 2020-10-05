import numbers


config_data_types = {
    'string': str,
    'number': numbers.Number,
    'boolean': bool,
    'null': type(None),
    'object': dict,
    'array': list,

    'any': object,

    'int': int,
    'float': float,
}
