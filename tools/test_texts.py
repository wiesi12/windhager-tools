from windhager_tools.texts import TextDatabase

texts = TextDatabase()

texts.load_levels(
    "data/EbenenTexte_de.xml"
)

print()

print(
    texts.level_name(
        14,
        113,
    )
)

print(
    texts.level_name(
        14,
        117,
    )
)

print(
    texts.level_name(
        15,
        100,
    )
)