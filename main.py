import cv2
import numpy as np
import os

#Nomes: Carlos, Lucas, Mauro

# Adiciono esta função no início do código
def pixel_para_casa_xadrez(x, y, w_caixa, h_caixa, largura_imagem, altura_imagem):
    # O tamanho de cada "casa" (quadrado) do tabuleiro
    tamanho_casa_x = largura_imagem / 8
    tamanho_casa_y = altura_imagem / 8

    # Vamos usar o centro da caixa delimitadora para garantir precisão
    centro_x = x + (w_caixa / 2)
    centro_y = y + (h_caixa / 2)
    
    # Calcula o índice da coluna (0 a 7) e da linha (0 a 7)
    coluna_idx = int(centro_x // tamanho_casa_x)
    linha_idx = int(centro_y // tamanho_casa_y)
    
    # Converte os índices para a notação do xadrez
    colunas_letras = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h']
    
    # As linhas no xadrez começam do 8 (topo) para 1 (baixo)
    # Se o y=0 é o topo da imagem, então a linha 0 da matriz é a linha "8" do xadrez.
    linha_numero = 8 - linha_idx
    
    # Evita erros se a detecção sair ligeiramente da tela
    coluna_idx = max(0, min(7, coluna_idx))
    linha_numero = max(1, min(8, linha_numero))
    
    return f"{colunas_letras[coluna_idx]}{linha_numero}"

# 1. Carrega o tabuleiro
tabuleiro_img = cv2.imread('./imagens/img1.png')
tabuleiro_gray = cv2.cvtColor(tabuleiro_img, cv2.COLOR_BGR2GRAY)

# 2. Dicionário de templates 
templates = {
    "peao_branco": "./templates/peao_branco.png",
    "peao_branco_casa_branca": "./templates/peao_branco_casa_branca.png",
    "torre_branca": "./templates/torre_branca.png",
    "cavalo_branco": "./templates/cavalo_branco.png",
    "bispo_branco": "./templates/bispo_branco.png",
    "rainha_branca": "./templates/rainha_branca.png",
    "rei_branco": "./templates/rei_branco.png",
    
    "peao_preto": "./templates/peao_preto.png",
    "torre_preta": "./templates/torre_preta.png",
    "cavalo_preto": "./templates/cavalo_preto.png",
    "bispo_preto": "./templates/bispo_preto.png",
    "rainha_preta": "./templates/rainha_preta.png",
    "rei_preto": "./templates/rei_preto.png"
}

# 3. Função para detectar as peças
def detectar_pecas(nome_peca, caminho_template, limiar=0.90):
    if not os.path.exists(caminho_template):
        print(f"Template não encontrado: {caminho_template}")
        return []
        
    template_img = cv2.imread(caminho_template, cv2.IMREAD_GRAYSCALE)
    w, h = template_img.shape[::-1]

    # Template Matching
    res = cv2.matchTemplate(tabuleiro_gray, template_img, cv2.TM_CCOEFF_NORMED)
    loc = np.where(res >= limiar)

    rectangles = []
    for pt in zip(*loc[::-1]):
        confianca = res[pt[1], pt[0]]
        rectangles.append([int(pt[0]), int(pt[1]), int(w), int(h), float(confianca)])

    # NMS (Supressão de não-máximos)
    boxes = [r[:4] for r in rectangles]
    scores = [r[4] for r in rectangles]
    indices_suprimidos = cv2.dnn.NMSBoxes(boxes, scores, limiar, 0.2)

    resultados_finais = []
    if len(indices_suprimidos) > 0:
        for i in indices_suprimidos.flatten():
            resultados_finais.append((boxes[i], scores[i], nome_peca))
            
    return resultados_finais

# 4. Rodar o detector para todas as peças do dicionário
todas_as_deteccoes = []
for nome_peca, caminho in templates.items():
    deteccoes = detectar_pecas(nome_peca, caminho, limiar=0.72)
    todas_as_deteccoes.extend(deteccoes)

# 5. Processamento Final: Mapear casas, gerar JSON e Desenhar
altura_img, largura_img = tabuleiro_img.shape[:2]
pecas_para_ia = []

for box, confianca, nome_arquivo in todas_as_deteccoes:
    x, y, w, h = box
    
    # Verifica a cor pelo nome da chave do dicionário
    is_branca = "branco" in nome_arquivo or "branca" in nome_arquivo
    cor_caixa = (255, 200, 0) if is_branca else (0, 0, 255)
    
    # 1. Tratamento de nome para a IA (ex: "peao_branco_casa_branca" -> "peao", "branco")
    cor_ia = "branco" if is_branca else "preto"
    tipo_ia = nome_arquivo.split('_')[0] 
    
    # 2. Converte as coordenadas do pixel para o formato do Xadrez (ex: "e4")
    casa = pixel_para_casa_xadrez(x, y, w, h, largura_img, altura_img)
    
    # 3. Monta o dicionário e salva
    pecas_para_ia.append({
        "tipo": tipo_ia,
        "cor": cor_ia,
        "casa": casa
    })

    # Desenha o retângulo na peça
    cv2.rectangle(tabuleiro_img, (x, y), (x + w, y + h), cor_caixa, 2)
    # Mostra a casa identificada em vez do "nome técnico do template"
    texto = f'{tipo_ia} em {casa}'
    cv2.putText(tabuleiro_img, texto, (x, y - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.4, cor_caixa, 1)

# Imprime a estrutura pronta que será usada no bônus (ia_xadrez.py)
print("pecas =", pecas_para_ia)

# Exibe o resultado final com as caixas
tabuleiro_img_redimensionada = cv2.resize(tabuleiro_img, (1024,768), cv2.INTER_LINEAR)
cv2.imshow('Tabuleiro Analisado', tabuleiro_img_redimensionada)
cv2.waitKey(0)
cv2.destroyAllWindows()