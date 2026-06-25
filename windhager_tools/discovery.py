from windhager_tools.models import Module, Function, Lookup


def discover_modules(client):

    modules = []

    data = client.lookup("1")

    for item in data:

        module = Module(
            id=item["nodeId"],
            name=item["name"],
            group=item["group"],
            subnet=item["subnet"],
            program_id=item["programId"],
            neuron_id=item["neuronId"]
        )

        modules.append(module)

    return modules


def discover_functions(client, module):

    data = client.lookup(f"1/{module.id}")

    functions = []

    for item in data["functions"]:

        function = Function(
            id=item["fctId"],
            type=item["fctType"],
            name=item["name"],
            locked=item["lock"]
        )

        functions.append(function)

    module.functions = functions

    return functions


def discover_lookups(client, module, function):

    data = client.lookup(
        f"1/{module.id}/{function.id}"
    )

    lookups = []

    for item in data:

        lookup = Lookup(
            id=item["id"],
            count=item["count"]
        )

        lookups.append(lookup)

    function.lookups = lookups

    return lookups