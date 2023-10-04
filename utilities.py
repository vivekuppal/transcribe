import copy

def merge(first: dict, second: dict, path=[]):
    """Recursively merge two dictionaries.
       For keys with different values, values in the second dictionary
       replace the values with current dictionary
    """
    if second is None:
        # No values to merge into first dict. Leave first dict unchanged.
        return
    if first is None:
        # First dict does not exist as yet, but second does.
        # Make a deepcopy of second and append to first
        first = copy.deepcopy(second)
        return

    for key in second:
        if key in first:
            if isinstance(first[key], dict) and isinstance(second[key], dict):
                merge(first[key], second[key], path + [str(key)])
            elif first[key] != second[key]:
                print(f'Replacing the value of {key} from {first[key]} to {second[key]}')
                first[key] = second[key]
        else:
            first[key] = second[key]
    return first
