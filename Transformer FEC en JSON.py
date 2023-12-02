import pandas as pd
import json

def convertir_fec_en_json(nom_fichier):
    # Lecture du fichier FEC
    df = pd.read_csv(nom_fichier, sep='\t', encoding='ISO-8859-1')

    # Regroupement des lignes par EcritureNum
    groupe_ecritures = df.groupby('EcritureNum')

    # Création d'une liste pour stocker les données JSON
    json_data = []

    # Itération sur chaque groupe et conversion en JSON
    for _, groupe in groupe_ecritures:
        # Convertir le DataFrame en dictionnaire et l'ajouter à la liste
        json_data.append(groupe.to_dict(orient='records'))

    # Conversion de la liste en JSON
    json_resultat = json.dumps(json_data, indent=2, ensure_ascii=False)

    # Sauvegarde du résultat dans un fichier JSON
    with open('FEC.json', 'w', encoding='utf-8') as file:
        file.write(json_resultat)

    return "Conversion réussie, fichier sauvegardé sous 'FEC.json'."

# Appel de la fonction
convertir_fec_en_json(r'path/to/your_FEC_file.txt')



