from typing import Any

import httpx


def normalize_digits(value: str) -> str:
    return "".join(ch for ch in value if ch.isdigit())


async def lookup_cnpj_receita(cnpj: str) -> dict[str, Any]:
    """
    Busca dados públicos de CNPJ.
    Esta implementação usa BrasilAPI como fonte pública para MVP.
    """
    cnpj_digits = normalize_digits(cnpj)
    if len(cnpj_digits) != 14:
        raise ValueError("CNPJ deve ter 14 dígitos.")

    url = f"https://brasilapi.com.br/api/cnpj/v1/{cnpj_digits}"
    async with httpx.AsyncClient(timeout=12.0) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        data = resp.json()

    return {
        "cnpj": cnpj_digits,
        "razao_social": data.get("razao_social"),
        "nome_fantasia": data.get("nome_fantasia"),
        "email": data.get("email"),
        "telefone": data.get("ddd_telefone_1"),
        "cep": normalize_digits(data.get("cep") or ""),
        "logradouro": data.get("logradouro"),
        "numero": data.get("numero"),
        "bairro": data.get("bairro"),
        "cidade": data.get("municipio"),
        "estado": data.get("uf"),
    }


async def lookup_cep(cep: str) -> dict[str, Any]:
    cep_digits = normalize_digits(cep)
    if len(cep_digits) != 8:
        raise ValueError("CEP deve ter 8 dígitos.")

    url = f"https://viacep.com.br/ws/{cep_digits}/json/"
    async with httpx.AsyncClient(timeout=12.0) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        data = resp.json()

    if data.get("erro"):
        raise ValueError("CEP não encontrado.")

    return {
        "cep": cep_digits,
        "logradouro": data.get("logradouro"),
        "bairro": data.get("bairro"),
        "cidade": data.get("localidade"),
        "estado": data.get("uf"),
    }
