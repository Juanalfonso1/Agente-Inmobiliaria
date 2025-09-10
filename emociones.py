from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

def detectar_emocion(texto):
    analizador = SentimentIntensityAnalyzer()
    resultado = analizador.polarity_scores(texto)
    compound = resultado['compound']
    
    if compound <= -0.5:
        return "frustrado"
    elif compound >= 0.5:
        return "positivo"
    else:
        return "neutral"
