from dashboard.llm.merchant import merchant_key


def test_card_payments_keep_only_the_merchant():
    assert merchant_key("Pago Movil En Lush Alcala, Madrid, Tarj. :*000000") == "lush alcala"
    assert merchant_key("PAGO MOVIL EN Dia 16023, Madrid, Tarj. :*000000") == "dia"
    assert merchant_key("Compra Tienda Norte, Madrid, Tarjeta 5400000000000000 , Comision 0,00") == "tienda norte"


def test_same_merchant_with_different_references_gets_the_same_key():
    first = merchant_key("Recibo Luz Sol S.l. N° Recibo 0049 0516 143")
    second = merchant_key("Recibo Luz Sol S.l. N° Recibo 0049 0617 222")

    assert first == second == "luz sol"


def test_accents_case_and_generic_prefixes_do_not_matter():
    assert merchant_key("Liquidación Periódica Préstamo 0049 0516") == "prestamo"
    assert merchant_key("TRANSFERENCIA A FAVOR DE Ana Pérez Concepto: x") == "ana perez concepto"


def test_empty_or_numeric_concepts_give_an_empty_key():
    assert merchant_key("") == ""
    assert merchant_key("1234 5678") == ""
