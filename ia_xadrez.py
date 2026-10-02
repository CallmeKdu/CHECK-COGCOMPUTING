"""IA de xadrez autocontida para receber o estado detectado do tabuleiro.

O contrato publico e ``melhor_jogada(pecas, turno)``. Roque e en passant nao
sao suportados porque nao podem ser deduzidos apenas por uma imagem do tabuleiro.
"""

from math import inf
from typing import Final

BRANCO: Final = "branco"
PRETO: Final = "preto"
CORES: Final = {BRANCO, PRETO}
TIPOS: Final = {"peao", "torre", "cavalo", "bispo", "rainha", "rei"}
VALOR: Final = {
    "peao": 100,
    "cavalo": 320,
    "bispo": 330,
    "torre": 500,
    "rainha": 900,
    "rei": 20_000,
}
DIRECOES_TORRE: Final = ((1, 0), (-1, 0), (0, 1), (0, -1))
DIRECOES_BISPO: Final = ((1, 1), (1, -1), (-1, 1), (-1, -1))
SALTOS_CAVALO: Final = (
    (1, 2),
    (2, 1),
    (2, -1),
    (1, -2),
    (-1, -2),
    (-2, -1),
    (-2, 1),
    (-1, 2),
)

Casa = tuple[int, int]
Peca = tuple[str, str]
Tabuleiro = dict[Casa, Peca]
Movimento = tuple[Casa, Casa, str | None]


def melhor_jogada(pecas: list[dict[str, str]], turno: str, profundidade: int = 3) -> str:
    """Retorna a melhor jogada legal em notacao UCI.

    Args:
        pecas: Itens com as chaves ``tipo``, ``cor`` e ``casa``. Exemplo:
            ``{"tipo": "cavalo", "cor": "branco", "casa": "g1"}``.
        turno: ``"branco"`` ou ``"preto"``.
        profundidade: Numero de meio-lances pesquisados pelo Minimax, no minimo 1.

    Returns:
        Uma jogada UCI, como ``"g1f3"`` ou ``"e7e8q"`` em uma promocao.

    Raises:
        ValueError: Se o estado for invalido, a profundidade for invalida ou nao
            houver uma jogada legal para o jogador da vez.
    """
    if turno not in CORES:
        raise ValueError("turno deve ser 'branco' ou 'preto'.")
    if not isinstance(profundidade, int) or profundidade < 1:
        raise ValueError("profundidade deve ser um inteiro maior ou igual a 1.")

    tabuleiro = _montar_tabuleiro(pecas)
    jogadas = _jogadas_legais(tabuleiro, turno)
    if not jogadas:
        raise ValueError("Nao ha jogadas legais para o jogador da vez.")

    adversario = _outra_cor(turno)
    melhor: Movimento | None = None
    melhor_valor = -inf
    alpha, beta = -inf, inf
    for movimento in sorted(jogadas, key=_uci):
        valor = _minimax(
            _aplicar(tabuleiro, movimento),
            adversario,
            turno,
            profundidade - 1,
            alpha,
            beta,
        )
        if valor > melhor_valor:
            melhor_valor = valor
            melhor = movimento
        alpha = max(alpha, melhor_valor)

    assert melhor is not None
    return _uci(melhor)


def _montar_tabuleiro(pecas: list[dict[str, str]]) -> Tabuleiro:
    if not isinstance(pecas, list):
        raise ValueError("pecas deve ser uma lista.")

    tabuleiro: Tabuleiro = {}
    reis = {BRANCO: 0, PRETO: 0}
    for indice, peca in enumerate(pecas):
        if not isinstance(peca, dict):
            raise ValueError(f"peca {indice} deve ser um dicionario.")
        try:
            tipo = peca["tipo"]
            cor = peca["cor"]
            casa_texto = peca["casa"]
        except KeyError as erro:
            raise ValueError(f"peca {indice} deve conter tipo, cor e casa.") from erro
        if tipo not in TIPOS:
            raise ValueError(f"tipo invalido na peca {indice}: {tipo!r}.")
        if cor not in CORES:
            raise ValueError(f"cor invalida na peca {indice}: {cor!r}.")
        casa = _casa_para_coordenada(casa_texto)
        if casa in tabuleiro:
            raise ValueError(f"ha mais de uma peca na casa {casa_texto!r}.")
        tabuleiro[casa] = (cor, tipo)
        if tipo == "rei":
            reis[cor] += 1

    if reis != {BRANCO: 1, PRETO: 1}:
        raise ValueError("a posicao deve conter exatamente um rei de cada cor.")
    return tabuleiro


def _minimax(
    tabuleiro: Tabuleiro,
    turno: str,
    perspectiva: str,
    profundidade: int,
    alpha: float,
    beta: float,
) -> float:
    jogadas = _jogadas_legais(tabuleiro, turno)
    if not jogadas:
        if _em_xeque(tabuleiro, turno):
            return -100_000 - profundidade if turno == perspectiva else 100_000 + profundidade
        return 0
    if profundidade == 0:
        return _avaliar(tabuleiro, perspectiva)

    maximizando = turno == perspectiva
    melhor_valor = -inf if maximizando else inf
    proximo_turno = _outra_cor(turno)
    for movimento in sorted(jogadas, key=_uci):
        valor = _minimax(
            _aplicar(tabuleiro, movimento),
            proximo_turno,
            perspectiva,
            profundidade - 1,
            alpha,
            beta,
        )
        if maximizando:
            melhor_valor = max(melhor_valor, valor)
            alpha = max(alpha, melhor_valor)
        else:
            melhor_valor = min(melhor_valor, valor)
            beta = min(beta, melhor_valor)
        if beta <= alpha:
            break
    return melhor_valor


def _avaliar(tabuleiro: Tabuleiro, perspectiva: str) -> float:
    adversario = _outra_cor(perspectiva)
    material = sum(
        VALOR[tipo] if cor == perspectiva else -VALOR[tipo]
        for cor, tipo in tabuleiro.values()
    )
    mobilidade = len(_jogadas_legais(tabuleiro, perspectiva)) - len(
        _jogadas_legais(tabuleiro, adversario)
    )
    return material + mobilidade * 2


def _jogadas_legais(tabuleiro: Tabuleiro, cor: str) -> list[Movimento]:
    return [
        movimento
        for movimento in _jogadas_pseudo_legais(tabuleiro, cor)
        if not _em_xeque(_aplicar(tabuleiro, movimento), cor)
    ]


def _jogadas_pseudo_legais(tabuleiro: Tabuleiro, cor: str) -> list[Movimento]:
    movimentos: list[Movimento] = []
    for origem, (cor_peca, tipo) in tabuleiro.items():
        if cor_peca != cor:
            continue
        if tipo == "peao":
            movimentos.extend(_jogadas_peao(tabuleiro, origem, cor))
        elif tipo == "cavalo":
            movimentos.extend(_jogadas_saltador(tabuleiro, origem, cor, SALTOS_CAVALO))
        elif tipo == "rei":
            movimentos.extend(_jogadas_saltador(tabuleiro, origem, cor, DIRECOES_TORRE + DIRECOES_BISPO))
        elif tipo == "torre":
            movimentos.extend(_jogadas_deslizante(tabuleiro, origem, cor, DIRECOES_TORRE))
        elif tipo == "bispo":
            movimentos.extend(_jogadas_deslizante(tabuleiro, origem, cor, DIRECOES_BISPO))
        else:
            movimentos.extend(
                _jogadas_deslizante(tabuleiro, origem, cor, DIRECOES_TORRE + DIRECOES_BISPO)
            )
    return movimentos


def _jogadas_peao(tabuleiro: Tabuleiro, origem: Casa, cor: str) -> list[Movimento]:
    arquivo, fileira = origem
    direcao = 1 if cor == BRANCO else -1
    inicio = 1 if cor == BRANCO else 6
    promocao = 7 if cor == BRANCO else 0
    movimentos: list[Movimento] = []
    frente = (arquivo, fileira + direcao)
    if _dentro(frente) and frente not in tabuleiro:
        movimentos.append((origem, frente, "rainha" if frente[1] == promocao else None))
        salto = (arquivo, fileira + 2 * direcao)
        if fileira == inicio and salto not in tabuleiro:
            movimentos.append((origem, salto, None))
    for deslocamento in (-1, 1):
        destino = (arquivo + deslocamento, fileira + direcao)
        alvo = tabuleiro.get(destino)
        if _dentro(destino) and alvo is not None and alvo[0] != cor and alvo[1] != "rei":
            movimentos.append((origem, destino, "rainha" if destino[1] == promocao else None))
    return movimentos


def _jogadas_saltador(
    tabuleiro: Tabuleiro, origem: Casa, cor: str, direcoes: tuple[Casa, ...]
) -> list[Movimento]:
    movimentos: list[Movimento] = []
    for delta_arquivo, delta_fileira in direcoes:
        destino = (origem[0] + delta_arquivo, origem[1] + delta_fileira)
        alvo = tabuleiro.get(destino)
        if _dentro(destino) and (alvo is None or (alvo[0] != cor and alvo[1] != "rei")):
            movimentos.append((origem, destino, None))
    return movimentos


def _jogadas_deslizante(
    tabuleiro: Tabuleiro, origem: Casa, cor: str, direcoes: tuple[Casa, ...]
) -> list[Movimento]:
    movimentos: list[Movimento] = []
    for delta_arquivo, delta_fileira in direcoes:
        arquivo, fileira = origem
        while True:
            arquivo += delta_arquivo
            fileira += delta_fileira
            destino = (arquivo, fileira)
            if not _dentro(destino):
                break
            alvo = tabuleiro.get(destino)
            if alvo is None:
                movimentos.append((origem, destino, None))
                continue
            if alvo[0] != cor and alvo[1] != "rei":
                movimentos.append((origem, destino, None))
            break
    return movimentos


def _em_xeque(tabuleiro: Tabuleiro, cor: str) -> bool:
    rei = next((casa for casa, (cor_peca, tipo) in tabuleiro.items() if cor_peca == cor and tipo == "rei"), None)
    if rei is None:
        return True
    return _casa_atacada(tabuleiro, rei, _outra_cor(cor))


def _casa_atacada(tabuleiro: Tabuleiro, casa: Casa, atacante: str) -> bool:
    arquivo, fileira = casa
    direcao_peao = -1 if atacante == BRANCO else 1
    for deslocamento in (-1, 1):
        peca = tabuleiro.get((arquivo + deslocamento, fileira + direcao_peao))
        if peca == (atacante, "peao"):
            return True
    for delta_arquivo, delta_fileira in SALTOS_CAVALO:
        if tabuleiro.get((arquivo + delta_arquivo, fileira + delta_fileira)) == (atacante, "cavalo"):
            return True
    for delta_arquivo, delta_fileira in DIRECOES_TORRE + DIRECOES_BISPO:
        origem = (arquivo + delta_arquivo, fileira + delta_fileira)
        if tabuleiro.get(origem) == (atacante, "rei"):
            return True
    return _atacada_por_deslizante(tabuleiro, casa, atacante, DIRECOES_TORRE, {"torre", "rainha"}) or _atacada_por_deslizante(
        tabuleiro, casa, atacante, DIRECOES_BISPO, {"bispo", "rainha"}
    )


def _atacada_por_deslizante(
    tabuleiro: Tabuleiro, casa: Casa, atacante: str, direcoes: tuple[Casa, ...], tipos: set[str]
) -> bool:
    for delta_arquivo, delta_fileira in direcoes:
        arquivo, fileira = casa
        while True:
            arquivo += delta_arquivo
            fileira += delta_fileira
            origem = (arquivo, fileira)
            if not _dentro(origem):
                break
            peca = tabuleiro.get(origem)
            if peca is None:
                continue
            if peca[0] == atacante and peca[1] in tipos:
                return True
            break
    return False


def _aplicar(tabuleiro: Tabuleiro, movimento: Movimento) -> Tabuleiro:
    origem, destino, promocao = movimento
    proximo = tabuleiro.copy()
    cor, tipo = proximo.pop(origem)
    proximo[destino] = (cor, promocao or tipo)
    return proximo


def _casa_para_coordenada(casa: str) -> Casa:
    if not isinstance(casa, str) or len(casa) != 2 or casa[0] not in "abcdefgh" or casa[1] not in "12345678":
        raise ValueError(f"casa invalida: {casa!r}.")
    return ord(casa[0]) - ord("a"), int(casa[1]) - 1


def _texto_casa(casa: Casa) -> str:
    return f"{chr(ord('a') + casa[0])}{casa[1] + 1}"


def _uci(movimento: Movimento) -> str:
    origem, destino, promocao = movimento
    sufixo = "q" if promocao == "rainha" else ""
    return f"{_texto_casa(origem)}{_texto_casa(destino)}{sufixo}"


def _outra_cor(cor: str) -> str:
    return PRETO if cor == BRANCO else BRANCO


def _dentro(casa: Casa) -> bool:
    return 0 <= casa[0] < 8 and 0 <= casa[1] < 8