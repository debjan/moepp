"""Region and station mappings for MOEPP API."""

# Region to stations mapping
# Each region contains specific station IDs
REGION_STATIONS = {
    '1': ['31', '48', '32', '46', '64', '44', '1'],
    '2': ['38', '39', '50', '36', '43', '58', '52', '42'],
    '3': ['53', '41', '51', '45', '35', '37', '49'],
}

STATION_NAMES = {
    '1': {'name': 'ЦЕНТАР', 'name_en': 'CENTAR'},
    '31': {'name': 'ГАЗИ БАБА', 'name_en': 'GAZI BABA'},
    '32': {'name': 'ЛИСИЧЕ', 'name_en': 'LISICE'},
    '35': {'name': 'КОЧАНИ', 'name_en': 'KOCHANI'},
    '36': {'name': 'КИЧЕВО', 'name_en': 'KICHEVO'},
    '37': {'name': 'КУМАНОВО', 'name_en': 'KUMANOVO'},
    '38': {'name': 'БИТОЛА 1', 'name_en': 'BITOLA 1'},
    '39': {'name': 'БИТОЛА 2', 'name_en': 'BITOLA 2'},
    '41': {'name': 'ВЕЛЕС 2', 'name_en': 'VELES 2'},
    '42': {'name': 'ТЕТОВО', 'name_en': 'TETOVO'},
    '43': {'name': 'ЛАЗАРОПОЛЕ', 'name_en': 'LAZAROPOLE'},
    '44': {'name': 'РЕКТОРАТ', 'name_en': 'RECTORATE'},
    '45': {'name': 'КАВАДАРЦИ', 'name_en': 'KAVADARCI'},
    '46': {'name': 'МИЛАДИНОВЦИ', 'name_en': 'MILADINOVCI'},
    '48': {'name': 'КАРПОШ', 'name_en': 'KARPOSH'},
    '49': {'name': 'СТРУМИЦА', 'name_en': 'STRUMICA'},
    '50': {'name': 'ГОСТИВАР', 'name_en': 'GOSTIVAR'},
    '51': {'name': 'ГЕВГЕЛИЈА', 'name_en': 'GEVGELIJA'},
    '52': {'name': 'ПРИЛЕП', 'name_en': 'PRILEP'},
    '53': {'name': 'БЕРОВО', 'name_en': 'BEROVO'},
    '58': {'name': 'ОХРИД', 'name_en': 'OHRID'},
    '64': {'name': 'МОБИЛНА ЃП', 'name_en': 'MOBILE GP'},
}

ALL_STATION_IDS = list(STATION_NAMES.keys())

ALL_REGION_IDS = list(REGION_STATIONS.keys())

