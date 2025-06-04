
# FEC to JSON Converter

- [🇬🇧 English Version](#-english-version)
- [🇫🇷 Version Française](#-version-française)

---

## 🇬🇧 English Version

### Description
This project contains a Python script for converting FEC (Fichier des Écritures Comptables) files into JSON format. It reads the FEC file, groups the lines by accounting entry number, and converts them into a structured JSON format.

### Features
- Reads FEC files in text format.
- Groups data by accounting entry number.
- Converts data into JSON format.
- Exports the result as a JSON file.

### Prerequisites
- Python 3
- Pandas Library

### Installation
Ensure Python is installed on your machine. To install Pandas, run the following command:
```
pip install pandas
```

### Usage
Follow these steps to use this script:
1. Place your FEC file in the same directory as the script or specify the file path in the script.
2. Run the script by passing the FEC file path as an argument.
3. The script will generate a JSON file in the same directory.

### Example
```
convertir_fec_en_json('path/to/your_FEC_file.txt')
```

### License
This project is licensed under GNU Affero General Public License v3.0. See the `LICENSE` file for more details.

### Contact
For any questions or suggestions, feel free to contact me on Twitter [@FabriceHeuvrard](https://twitter.com/FabriceHeuvrard) or LinkedIn: https://www.linkedin.com/in/fabriceheuvrard/

---

## 🇫🇷 Version Française

### Description
Ce projet contient un script Python pour convertir les fichiers FEC (Fichier des Écritures Comptables) en format JSON. Il lit le fichier FEC, regroupe les lignes par numéro d'écriture comptable, et les convertit en un format JSON structuré.

### Fonctionnalités
- Lit les fichiers FEC au format texte.
- Regroupe les données par numéro d'écriture comptable.
- Convertit les données en format JSON.
- Exporte le résultat en tant que fichier JSON.

### Prérequis
- Python 3
- Bibliothèque Pandas

### Installation
Assurez-vous que Python est installé sur votre machine. Pour installer Pandas, exécutez la commande suivante :
```
pip install pandas
```

### Utilisation
Suivez ces étapes pour utiliser ce script :
1. Placez votre fichier FEC dans le même répertoire que le script ou spécifiez le chemin du fichier dans le script.
2. Exécutez le script en passant le chemin du fichier FEC en argument.
3. Le script générera un fichier JSON dans le même répertoire.

### Exemple
```
convertir_fec_en_json('chemin/vers/votre_fichier_FEC.txt')
```
### Licence
Ce projet est sous licence GNU Affero General Public License v3.0. Voir le fichier `LICENSE` pour plus de détails.

### Contact
Pour toute question ou suggestion, n'hésitez pas à me contacter sur Twitter [@FabriceHeuvrard](https://twitter.com/FabriceHeuvrard) ou sur LinkedIn: https://www.linkedin.com/in/fabriceheuvrard/
