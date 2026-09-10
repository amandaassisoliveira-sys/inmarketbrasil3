from fastapi import APIRouter
from pydantic import BaseModel
import httpx
import asyncio
import unicodedata

router = APIRouter(prefix="/tax", tags=["tax"])

UF_RATES = {
    "AC": 17, "AL": 18, "AP": 18, "AM": 18, "BA": 18, "CE": 18, "DF": 18, "ES": 17, "GO": 17,
    "MA": 18, "MT": 17, "MS": 17, "MG": 18, "PA": 18, "PB": 18, "PR": 18, "PE": 18, "PI": 18,
    "RJ": 18, "RN": 18, "RS": 17, "RO": 17.5, "RR": 17, "SC": 17, "SP": 18, "SE": 18, "TO": 18,
}


def _normalize(s: str) -> str:
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return s.lower()


# ---------------------------------------------------------------------------
# Catálogo local curado — usado como fallback quando a API externa (abaixo)
# está indisponível, e também para busca direta por código NCM/HS.
# ---------------------------------------------------------------------------
NCM_TABLE = {
    "calcados": [
        {"kw": ["couro", "social", "masculino"], "code": "6403.99.90", "desc": "Calçados com sola de borracha/plástico e parte superior de couro natural", "reg": [], "ii": 35, "ipi": 0},
        {"kw": ["sintetico", "tenis", "esportivo", "corrida"], "code": "6404.11.00", "desc": "Calçados de desporto, com parte superior de matérias têxteis", "reg": [], "ii": 35, "ipi": 0},
        {"kw": ["chinelo", "sandalia", "borracha"], "code": "6402.99.90", "desc": "Outros calçados com sola e parte superior de borracha ou plástico", "reg": [], "ii": 35, "ipi": 0},
        {"kw": ["infantil", "bebe", "crianca"], "code": "6403.20.00", "desc": "Calçados infantis com parte superior de tiras de couro natural", "reg": [], "ii": 35, "ipi": 0},
    ],
    "intima": [
        {"kw": ["sutia", "renda", "bojo"], "code": "6212.10.00", "desc": "Sutiãs (soutiens), mesmo de malha", "reg": [], "ii": 35, "ipi": 5},
        {"kw": ["calcinha", "cueca", "algodao"], "code": "6108.21.00", "desc": "Calcinhas e combinações, de malha de algodão", "reg": [], "ii": 35, "ipi": 5},
        {"kw": ["lingerie", "conjunto", "seda"], "code": "6208.91.00", "desc": "Camisolas e artigos semelhantes de algodão, não de malha", "reg": [], "ii": 35, "ipi": 5},
    ],
    "infantil": [
        {"kw": ["fralda"], "code": "9619.00.00", "desc": "Fraldas para bebês e artigos higiênicos semelhantes", "reg": ["ANVISA"], "ii": 18, "ipi": 0},
        {"kw": ["mamadeira", "bico"], "code": "3924.10.00", "desc": "Artigos de plástico para serviço de mesa ou de uso doméstico", "reg": ["ANVISA"], "ii": 18, "ipi": 5},
        {"kw": ["carrinho"], "code": "8715.00.00", "desc": "Carrinhos e artigos semelhantes para transporte de crianças", "reg": ["INMETRO"], "ii": 20, "ipi": 10},
        {"kw": ["brinquedo", "boneco", "boneca", "pelucia", "miniatura", "quebra-cabeca", "quebra cabeca", "jogo de tabuleiro", "action figure", "figura de acao"], "code": "9503.00.99", "desc": "Outros brinquedos (bonecos, pelúcias, jogos, miniaturas)", "reg": ["INMETRO"], "ii": 20, "ipi": 10},
    ],
    "eletronicos": [
        {"kw": ["smartphone", "celular", "iphone"], "code": "8517.13.00", "desc": "Telefones inteligentes (smartphones)", "reg": ["ANATEL", "INMETRO"], "ii": 16, "ipi": 15},
        {"kw": ["notebook", "laptop"], "code": "8471.30.19", "desc": "Máquinas automáticas de processamento de dados, portáteis", "reg": ["INMETRO"], "ii": 16, "ipi": 15},
        {"kw": ["tv", "televisor", "televisao"], "code": "8528.72.00", "desc": "Aparelhos receptores de televisão, a cores", "reg": ["INMETRO"], "ii": 20, "ipi": 20},
        {"kw": ["caixa de som", "speaker"], "code": "8518.22.00", "desc": "Alto-falantes múltiplos montados no mesmo gabinete", "reg": ["ANATEL", "INMETRO"], "ii": 20, "ipi": 15},
        {"kw": ["relogio", "smartwatch"], "code": "9102.12.00", "desc": "Relógios de pulso, elétricos, com mostrador opto-eletrônico", "reg": ["ANATEL", "INMETRO"], "ii": 20, "ipi": 15},
    ],
    "acessorios_eletronicos": [
        {"kw": ["cabo", "usb"], "code": "8544.42.00", "desc": "Cabos elétricos com conectores, para tensão ≤ 1.000V", "reg": ["INMETRO"], "ii": 16, "ipi": 10},
        {"kw": ["fone", "headphone", "earbud"], "code": "8518.30.00", "desc": "Fones de ouvido e auscultadores, mesmo combinados com microfone", "reg": ["ANATEL", "INMETRO"], "ii": 20, "ipi": 15},
        {"kw": ["carregador", "fonte"], "code": "8504.40.90", "desc": "Conversores estáticos (carregadores/fontes de alimentação)", "reg": ["INMETRO"], "ii": 16, "ipi": 15},
        {"kw": ["capinha", "capa de celular", "case"], "code": "3926.90.90", "desc": "Outras obras de plástico (capas e acessórios de proteção)", "reg": [], "ii": 18, "ipi": 10},
        {"kw": ["power bank", "bateria portatil"], "code": "8507.60.00", "desc": "Acumuladores elétricos de íons de lítio (power bank)", "reg": ["INMETRO"], "ii": 16, "ipi": 15},
    ],
    "utilidades_domesticas": [
        {"kw": ["panela", "frigideira"], "code": "7323.93.00", "desc": "Artigos de uso doméstico de aço inoxidável", "reg": [], "ii": 18, "ipi": 5},
        {"kw": ["talher", "garfo", "faca", "colher"], "code": "8215.99.00", "desc": "Colheres, garfos e artigos semelhantes de mesa/cozinha", "reg": [], "ii": 18, "ipi": 5},
        {"kw": ["copo", "taca", "vidro"], "code": "7013.37.00", "desc": "Objetos de vidro para serviço de mesa ou de cozinha", "reg": ["ANVISA"], "ii": 18, "ipi": 5},
        {"kw": ["organizador", "pote"], "code": "3924.90.00", "desc": "Outros artigos de plástico para uso doméstico", "reg": ["ANVISA"], "ii": 18, "ipi": 5},
    ],
    "cama_mesa_banho": [
        {"kw": ["lencol", "jogo de cama"], "code": "6302.21.00", "desc": "Roupas de cama, estampadas, de algodão, não de malha", "reg": [], "ii": 35, "ipi": 5},
        {"kw": ["toalha de banho", "toalha de rosto", "toalha"], "code": "6302.60.00", "desc": "Toalhas de toucador ou de cozinha, de tecido atoalhado de algodão", "reg": [], "ii": 35, "ipi": 5},
        {"kw": ["travesseiro", "almofada"], "code": "9404.90.00", "desc": "Outros artigos de cama e semelhantes (travesseiros, almofadas)", "reg": [], "ii": 20, "ipi": 5},
        {"kw": ["toalha de mesa", "cobre-leito", "edredom"], "code": "6302.59.00", "desc": "Toalhas de mesa e artigos semelhantes de outras matérias têxteis", "reg": [], "ii": 35, "ipi": 5},
    ],
    "vestuario": [
        {"kw": ["camiseta", "algodao"], "code": "6109.10.00", "desc": "Camisetas de malha de algodão", "reg": [], "ii": 35, "ipi": 5},
        {"kw": ["calca", "jeans"], "code": "6203.42.00", "desc": "Calças de algodão, para homens ou meninos", "reg": [], "ii": 35, "ipi": 5},
        {"kw": ["vestido"], "code": "6104.44.00", "desc": "Vestidos de malha de fibras sintéticas", "reg": [], "ii": 35, "ipi": 5},
    ],
    "animais_vivos": [
        {"kw": ["cachorro", "cao", "cachorros"], "code": "0106.19.00", "desc": "Outros animais vivos (mamíferos) — cães", "reg": ["MAPA/VIGIAGRO"], "ii": 0, "ipi": 0},
        {"kw": ["gato", "gatos", "felino"], "code": "0106.19.00", "desc": "Outros animais vivos (mamíferos) — gatos", "reg": ["MAPA/VIGIAGRO"], "ii": 0, "ipi": 0},
        {"kw": ["ave", "aves", "passaro", "passarinho"], "code": "0106.39.00", "desc": "Outros animais vivos — aves não especificadas", "reg": ["MAPA/VIGIAGRO"], "ii": 0, "ipi": 0},
        {"kw": ["peixe ornamental", "peixe", "aquario"], "code": "0301.19.00", "desc": "Outros peixes ornamentais vivos", "reg": ["MAPA/VIGIAGRO"], "ii": 0, "ipi": 0},
    ],
    "produtos_vegetais": [
        {"kw": ["semente", "sementes"], "code": "1209.99.00", "desc": "Outras sementes para semeadura", "reg": ["MAPA/VIGIAGRO"], "ii": 8, "ipi": 0},
        {"kw": ["muda", "mudas", "planta viva"], "code": "0602.90.00", "desc": "Outras plantas vivas", "reg": ["MAPA/VIGIAGRO"], "ii": 8, "ipi": 0},
        {"kw": ["flor seca", "flor artificial"], "code": "0603.90.00", "desc": "Outras flores e botões, cortados", "reg": ["MAPA/VIGIAGRO"], "ii": 8, "ipi": 0},
    ],
    "alimentos": [
        {"kw": ["suplemento", "whey", "proteina em po"], "code": "2106.90.90", "desc": "Outras preparações alimentícias (suplementos)", "reg": ["ANVISA"], "ii": 16, "ipi": 8},
        {"kw": ["cha", "cha em saquinho"], "code": "2101.20.00", "desc": "Extratos, essências e concentrados de chá", "reg": ["ANVISA"], "ii": 16, "ipi": 0},
        {"kw": ["doce", "bala", "chocolate"], "code": "1704.90.90", "desc": "Outras confeitarias sem cacau (doces, balas)", "reg": ["ANVISA"], "ii": 18, "ipi": 5},
        {"kw": ["bebida", "refrigerante", "energetico"], "code": "2202.99.00", "desc": "Outras bebidas não alcoólicas", "reg": ["ANVISA"], "ii": 20, "ipi": 4},
    ],
    "medicamentos": [
        {"kw": ["remedio", "medicamento", "comprimido", "farmaco"], "code": "3004.90.99", "desc": "Outros medicamentos para uso terapêutico, dosados", "reg": ["ANVISA"], "ii": 0, "ipi": 0},
        {"kw": ["vitamina", "multivitaminico"], "code": "3004.50.90", "desc": "Outros medicamentos contendo vitaminas", "reg": ["ANVISA"], "ii": 0, "ipi": 0},
        {"kw": ["curativo", "gaze", "band-aid"], "code": "3005.90.90", "desc": "Outros artigos de pensos, gazes e similares", "reg": ["ANVISA"], "ii": 14, "ipi": 0},
    ],
    "cosmeticos": [
        {"kw": ["perfume", "colonia"], "code": "3303.00.20", "desc": "Perfumes (extratos)", "reg": ["ANVISA"], "ii": 18, "ipi": 22},
        {"kw": ["batom", "maquiagem", "base facial"], "code": "3304.99.90", "desc": "Outros produtos de beleza ou de maquilagem", "reg": ["ANVISA"], "ii": 18, "ipi": 22},
        {"kw": ["shampoo", "condicionador", "xampu"], "code": "3305.10.00", "desc": "Xampus para o cabelo", "reg": ["ANVISA"], "ii": 18, "ipi": 22},
        {"kw": ["protetor solar", "filtro solar"], "code": "3304.99.10", "desc": "Protetores solares", "reg": ["ANVISA"], "ii": 18, "ipi": 22},
    ],
    "quimicos": [
        {"kw": ["tinta", "corante"], "code": "3208.90.90", "desc": "Outras tintas à base de polímeros sintéticos", "reg": [], "ii": 14, "ipi": 8},
        {"kw": ["cola", "adesivo"], "code": "3506.91.90", "desc": "Outros adesivos à base de polímeros", "reg": [], "ii": 14, "ipi": 8},
        {"kw": ["detergente", "sabao liquido", "limpeza"], "code": "3402.20.00", "desc": "Produtos de limpeza acondicionados para venda a retalho", "reg": ["ANVISA"], "ii": 18, "ipi": 8},
    ],
    "maquinas_indl": [
        {"kw": ["motor eletrico", "motor"], "code": "8501.10.10", "desc": "Motores elétricos de potência ≤ 37,5 W", "reg": ["INMETRO"], "ii": 14, "ipi": 5},
        {"kw": ["bomba dagua", "bomba de agua", "bomba hidraulica"], "code": "8413.70.90", "desc": "Outras bombas centrífugas", "reg": ["INMETRO"], "ii": 14, "ipi": 5},
        {"kw": ["compressor", "compressor de ar"], "code": "8414.80.90", "desc": "Outros compressores de ar ou gás", "reg": ["INMETRO"], "ii": 14, "ipi": 8},
        {"kw": ["gerador", "gerador de energia"], "code": "8502.20.00", "desc": "Grupos eletrogêneos com motor de pistão", "reg": ["INMETRO"], "ii": 14, "ipi": 8},
    ],
    "pecas_autopecas": [
        {"kw": ["pastilha de freio", "freio"], "code": "8708.30.90", "desc": "Outras partes de freios para veículos automóveis", "reg": ["INMETRO"], "ii": 18, "ipi": 12},
        {"kw": ["filtro de oleo", "filtro de ar", "filtro"], "code": "8421.23.00", "desc": "Aparelhos para filtrar óleos ou combustíveis em motores", "reg": [], "ii": 14, "ipi": 8},
        {"kw": ["parafuso", "porca", "arruela"], "code": "7318.15.00", "desc": "Outros parafusos e pinos, de ferro fundido/aço", "reg": [], "ii": 16, "ipi": 5},
        {"kw": ["rolamento", "rolamento de esfera"], "code": "8482.10.10", "desc": "Rolamentos de esferas", "reg": [], "ii": 14, "ipi": 5},
        {"kw": ["correia", "correia dentada"], "code": "4010.31.00", "desc": "Correias de transmissão de borracha vulcanizada", "reg": [], "ii": 16, "ipi": 5},
    ],
    "moveis": [
        {"kw": ["cadeira", "poltrona"], "code": "9401.61.00", "desc": "Outros assentos com armação de madeira, estofados", "reg": [], "ii": 20, "ipi": 5},
        {"kw": ["mesa", "mesa de escritorio"], "code": "9403.60.00", "desc": "Outros móveis de madeira", "reg": [], "ii": 20, "ipi": 5},
        {"kw": ["estante", "prateleira"], "code": "9403.20.00", "desc": "Outros móveis metálicos", "reg": [], "ii": 20, "ipi": 5},
    ],
    "ferramentas": [
        {"kw": ["chave de fenda", "chave de boca", "ferramenta manual"], "code": "8205.59.00", "desc": "Outras ferramentas manuais", "reg": [], "ii": 16, "ipi": 5},
        {"kw": ["furadeira", "parafusadeira"], "code": "8467.21.00", "desc": "Furadeiras de todos os tipos, elétricas", "reg": ["INMETRO"], "ii": 18, "ipi": 8},
        {"kw": ["serra eletrica", "serra circular"], "code": "8467.22.00", "desc": "Serras elétricas portáteis", "reg": ["INMETRO"], "ii": 18, "ipi": 8},
    ],
    "veiculos": [
        {"kw": ["motocicleta", "moto"], "code": "8711.20.90", "desc": "Motocicletas com motor de 50 a 250 cm³", "reg": ["INMETRO"], "ii": 20, "ipi": 20},
        {"kw": ["bicicleta eletrica", "e-bike"], "code": "8711.60.00", "desc": "Motocicletas/ciclos com motor elétrico de propulsão", "reg": ["INMETRO"], "ii": 20, "ipi": 12},
        {"kw": ["patinete eletrico", "scooter eletrico"], "code": "8711.60.00", "desc": "Veículos elétricos de duas rodas", "reg": ["INMETRO"], "ii": 20, "ipi": 12},
        {"kw": ["pneu"], "code": "4011.10.00", "desc": "Pneus novos de borracha para automóveis", "reg": ["INMETRO"], "ii": 16, "ipi": 12},
    ],
    "livros_papel": [
        {"kw": ["livro", "livro infantil"], "code": "4901.99.00", "desc": "Outros livros, brochuras e impressos semelhantes", "reg": [], "ii": 0, "ipi": 0},
        {"kw": ["caderno", "agenda"], "code": "4820.10.00", "desc": "Cadernos e agendas", "reg": [], "ii": 16, "ipi": 5},
        {"kw": ["caneta", "lapis"], "code": "9608.10.00", "desc": "Canetas esferográficas", "reg": [], "ii": 18, "ipi": 5},
    ],
    "joias": [
        {"kw": ["anel", "alianca"], "code": "7113.11.00", "desc": "Artigos de joalharia de prata", "reg": [], "ii": 18, "ipi": 0},
        {"kw": ["colar", "pulseira", "bijuteria"], "code": "7117.19.00", "desc": "Outras bijuterias de metais comuns", "reg": [], "ii": 18, "ipi": 15},
        {"kw": ["brinco"], "code": "7113.19.00", "desc": "Artigos de joalharia de outros metais preciosos", "reg": [], "ii": 18, "ipi": 0},
    ],
    "outros": [],
}


def _parece_codigo_ncm(desc: str) -> bool:
    so_digitos = "".join(c for c in desc if c.isdigit())
    return 4 <= len(so_digitos) <= 8


def _buscar_por_codigo_ncm(desc: str):
    so_digitos = "".join(c for c in desc if c.isdigit())
    if len(so_digitos) < 4:
        return None
    for categoria in NCM_TABLE.values():
        for item in categoria:
            codigo_digitos = "".join(c for c in item["code"] if c.isdigit())
            if codigo_digitos.startswith(so_digitos) or so_digitos.startswith(codigo_digitos[:6]):
                return item
    return None


# ---------------------------------------------------------------------------
# Base externa: tabelasfiscais.com.br — API gratuita e sem chave que espelha
# os dados oficiais (Siscomex/NCM + Receita Federal/TIPI + MDIC-Gecex/TEC),
# já cruzados com II e IPI por código. https://tabelasfiscais.com.br/api
#
# Contrato confirmado ao vivo (testado via terminal do próprio servidor):
#   GET /ncm/buscar?q={termo} -> {"resultados": [{"codigo","codigo_num","descricao","nivel","vigente"}]}
#   GET /ncm/{codigo_num}     -> {"codigo","descricao","ii":{"aliquota"},"ipi":{"aliquota"}}
# ---------------------------------------------------------------------------
TABELAS_FISCAIS_BASE = "https://tabelasfiscais.com.br/api/v1"


def _parse_aliquota(valor):
    if valor in (None, "NT", ""):
        return 0.0
    try:
        return float(valor)
    except (TypeError, ValueError):
        return 0.0


async def _get_com_retry(client, url, params=None, tentativas=2):
    ultima_resp = None
    for i in range(tentativas):
        resp = await client.get(url, params=params)
        ultima_resp = resp
        if resp.status_code == 200:
            return resp
        if resp.status_code in (502, 503, 504) and i < tentativas - 1:
            await asyncio.sleep(0.8)
            continue
        break
    return ultima_resp


async def _buscar_ncm_externo(query: str):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                      "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
        "Accept": "application/json",
    }
    try:
        async with httpx.AsyncClient(timeout=6.0, headers=headers) as client:
            resp_busca = await _get_com_retry(client, f"{TABELAS_FISCAIS_BASE}/ncm/buscar", params={"q": query})
            if resp_busca is None or resp_busca.status_code != 200:
                return None
            candidatos = resp_busca.json().get("resultados", [])
            if not candidatos:
                return None

            candidatos_ordenados = sorted(
                candidatos,
                key=lambda item: (item.get("nivel") == 8, item.get("vigente", True)),
                reverse=True,
            )
            melhor = candidatos_ordenados[0]
            if melhor.get("nivel") != 8:
                return None

            codigo_num = melhor.get("codigo_num") or melhor.get("codigo", "").replace(".", "")
            resp_detalhe = await _get_com_retry(client, f"{TABELAS_FISCAIS_BASE}/ncm/{codigo_num}")
            if resp_detalhe is None or resp_detalhe.status_code != 200:
                return None
            detalhe = resp_detalhe.json()
    except Exception:
        return None

    ii_aliquota = _parse_aliquota((detalhe.get("ii") or {}).get("aliquota"))
    ipi_aliquota = _parse_aliquota((detalhe.get("ipi") or {}).get("aliquota"))

    return {
        "code": detalhe.get("codigo", melhor.get("codigo", "—")),
        "desc": detalhe.get("descricao", melhor.get("descricao", "")),
        "ii": ii_aliquota,
        "ipi": ipi_aliquota,
        "fonte": "tabelasfiscais.com.br (dados oficiais Siscomex/TIPI/TEC)",
    }


class ClassifyRequest(BaseModel):
    descricao: str
    categoria: str
    hs_code: str = ""


@router.post("/classify")
async def classify_ncm(req: ClassifyRequest):
    # 1) HS Code do fornecedor, se informado — tenta local, depois externo
    if req.hs_code and _parece_codigo_ncm(req.hs_code):
        por_codigo = _buscar_por_codigo_ncm(req.hs_code)
        if por_codigo:
            return {
                "code": por_codigo["code"], "desc": por_codigo["desc"],
                "confidence": "encontrado pelo HS Code do fornecedor (catálogo local)",
                "reg": por_codigo.get("reg", []), "ii": por_codigo.get("ii", 0), "ipi": por_codigo.get("ipi", 0),
            }
        externo = await _buscar_ncm_externo(req.hs_code)
        if externo:
            return {
                "code": externo["code"], "desc": externo["desc"],
                "confidence": f"encontrado pelo HS Code via {externo['fonte']}",
                "reg": [], "ii": externo["ii"], "ipi": externo["ipi"],
            }

    # 2) Código dentro da própria descrição
    if _parece_codigo_ncm(req.descricao):
        por_codigo = _buscar_por_codigo_ncm(req.descricao)
        if por_codigo:
            return {
                "code": por_codigo["code"], "desc": por_codigo["desc"],
                "confidence": "encontrado por código NCM (catálogo local)",
                "reg": por_codigo.get("reg", []), "ii": por_codigo.get("ii", 0), "ipi": por_codigo.get("ipi", 0),
            }

    # 3) Busca externa por descrição
    if req.descricao:
        externo = await _buscar_ncm_externo(req.descricao)
        if externo:
            return {
                "code": externo["code"], "desc": externo["desc"],
                "confidence": f"encontrado via {externo['fonte']}",
                "reg": [], "ii": externo["ii"], "ipi": externo["ipi"],
            }

    # 4) Catálogo local por palavra-chave
    desc = _normalize(req.descricao)
    lista = NCM_TABLE.get(req.categoria, [])
    match = next((item for item in lista if any(_normalize(k) in desc for k in item["kw"])), None)
    if not match:
        msg = (
            "Não encontrado nem na base externa (tabelasfiscais.com.br) nem no catálogo local — "
            "refine a descrição, digite o próprio código NCM/HS se já souber, ou confirme com um despachante."
            if req.descricao
            else "Informe a descrição do produto para receber uma sugestão."
        )
        return {"code": "—", "desc": msg, "confidence": "sem correspondência", "reg": [], "ii": 0, "ipi": 0}
    return {
        "code": match["code"], "desc": match["desc"], "confidence": "sugestão automática (catálogo local)",
        "reg": match.get("reg", []), "ii": match.get("ii", 0), "ipi": match.get("ipi", 0),
    }


class SimplifiedTaxRequest(BaseModel):
    valor_mercadoria_usd: float
    frete_usd: float
    seguro_usd: float = 0
    uf: str
    pessoa: str = "pf"


@router.post("/simplified")
def calc_simplified_tax(req: SimplifiedTaxRequest):
    cif = req.valor_mercadoria_usd + req.frete_usd + req.seguro_usd

    if req.pessoa == "pf" and req.valor_mercadoria_usd <= 50:
        ii = 0.0
        regra = "Isento — Remessa Conforme, até US$ 50 (pessoa física)"
    elif req.pessoa == "pf":
        ii = max(0.0, cif * 0.60 - 30)
        regra = "60% sobre o valor aduaneiro, com dedução fixa de US$ 30"
    else:
        ii = cif * 0.60
        regra = "60% sobre o valor aduaneiro (pessoa jurídica, sem dedução do RTS)"

    aliquota_icms = UF_RATES.get(req.uf.upper(), 18) / 100
    base_icms = cif + ii
    icms = base_icms * aliquota_icms / (1 - aliquota_icms)

    return {
        "valor_aduaneiro_cif_usd": round(cif, 2),
        "ii_usd": round(ii, 2),
        "ii_regra": regra,
        "icms_usd": round(icms, 2),
        "icms_aliquota_pct": UF_RATES.get(req.uf.upper(), 18),
        "total_usd": round(cif + ii + icms, 2),
        "aviso": "Cálculo aproximado. Confirme a alíquota vigente e a regra do ICMS por dentro com um contador."
        if req.valor_mercadoria_usd <= 3000
        else "Valor acima de US$ 3.000 — esta operação exige importação formal.",
    }


class FormalTaxRequest(BaseModel):
    valor_fob_usd: float
    frete_usd: float
    seguro_usd: float = 0
    uf: str
    aliquota_ii_pct: float = 0
    aliquota_ipi_pct: float = 0


@router.post("/formal")
def calc_formal_tax(req: FormalTaxRequest):
    """
    II sobre CIF; IPI sobre CIF+II; ICMS "por dentro" sobre CIF+II+IPI.
    PIS/COFINS-Importação ainda não está incluído.
    """
    cif = req.valor_fob_usd + req.frete_usd + req.seguro_usd
    ii = cif * (req.aliquota_ii_pct / 100)
    ipi = (cif + ii) * (req.aliquota_ipi_pct / 100)

    aliquota_icms = UF_RATES.get(req.uf.upper(), 18) / 100
    base_icms = cif + ii + ipi
    icms = base_icms * aliquota_icms / (1 - aliquota_icms)

    return {
        "valor_aduaneiro_cif_usd": round(cif, 2),
        "ii_usd": round(ii, 2),
        "ii_aliquota_pct": req.aliquota_ii_pct,
        "ipi_usd": round(ipi, 2),
        "ipi_aliquota_pct": req.aliquota_ipi_pct,
        "icms_usd": round(icms, 2),
        "icms_aliquota_pct": UF_RATES.get(req.uf.upper(), 18),
        "total_impostos_usd": round(ii + ipi + icms, 2),
        "total_com_impostos_usd": round(cif + ii + ipi + icms, 2),
        "aviso": "Alíquotas de II/IPI são referências por tipo de produto, não pela NCM8 exata — "
                 "confirme no Simulador da Receita Federal ou com despachante antes de fechar. "
                 "PIS/COFINS-Importação ainda não está incluído neste cálculo.",
    }
