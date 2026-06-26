from .models import Entry, NvEntry


def read_lookup(client, module, function, lookup):

    data = client.lookup(
        f"1/{module.id}/{function.id}/{lookup.id}"
    )

    entries = []

    for item in data:

        if "OID" in item:

            entries.append(
                Entry(
                    oid=item["OID"],
                    value=item.get("value"),
                    unit=item.get("unit"),
                    type_id=item.get("typeId"),
                    write_protected=item.get("writeProt"),
                    group=item.get("groupNr"),
                    member=item.get("memberNr"),
                )
            )

        elif "nvName" in item:

            entries.append(
                NvEntry(
                    index=item["nvIndex"],
                    name=item["nvName"],
                    snvt_name=item.get("snvtName"),
                    snvt_index=item.get("snvtIndex"),
                    value=item.get("value"),
                    unit=item.get("unit")
                )
            )

    return entries