from frameedit.web_services.generation import normalize_category_name, normalize_product_name


def test_product_name_is_uppercase() -> None:
    assert normalize_product_name("  classical   bedset  ") == "CLASSICAL BEDSET"


def test_category_name_capitalizes_each_word() -> None:
    assert normalize_category_name("  bedroom sets  ") == "Bedroom Sets"
