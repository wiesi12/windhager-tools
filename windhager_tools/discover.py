import time


def discover_live_oids(client, catalog):

    live = []

    for node in catalog:

        print(f"\n{node['name']}")

        for function in node["functions"]:

            for lookup in function["lookups"]:

                for entry in lookup["entries"]:

                    oid = entry.get("oid")

                    if oid is None:
                        continue

                    try:

                        first = client.get(
                            f"datapoint{oid}"
                        )

                        time.sleep(0.05)

                        second = client.get(
                            f"datapoint{oid}"
                        )

                    except Exception:

                        continue

                    value1 = first.get("value")
                    value2 = second.get("value")

                    print(
                        f"{oid} -> {value1}"
                    )

                    live.append({
                        "oid": oid,
                        "value": value2,
                        "changed": value1 != value2,
                        "unit": entry.get("unit"),
                        "type": entry.get("type_id"),
                        "write": not entry.get("write_protected", True)
                    })

                    time.sleep(0.05)

    return live