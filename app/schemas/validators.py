from decimal import Decimal

def validate_duration(v: int | None) -> int | None:
    if v is not None and v < 15:
        raise ValueError("A duração mínima é de 15 minutos")
    return v

def validate_price(v: Decimal | None) -> Decimal | None:
    if v is not None and v < 0:
        raise ValueError("O preço não pode ser negativo")
    return v