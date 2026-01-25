"""
SIRE CONVERTER v3.0 - Motor de Conversión Inteligente
=====================================================

Características:
- Detección inteligente de columnas con fuzzy matching
- Análisis de contenido para identificar campos
- Motor de inferencia para campos faltantes
- Sistema de confianza para cada campo
- Validación robusta de datos
- Soporte para múltiples formatos

Autor: Police to SIRE Tool
"""

import re
import os
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

try:
    import pandas as pd
    import math
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False
    pd = None
    logger.warning("pandas no instalado. Instalar con: pip install pandas openpyxl")


def is_nan_or_empty(value) -> bool:
    """Verifica si un valor es NaN, None o vacío de forma segura."""
    if value is None:
        return True
    if isinstance(value, str):
        return value.strip() == ""
    if isinstance(value, float):
        try:
            return math.isnan(value)
        except (TypeError, ValueError):
            return False
    return False


class Confidence(Enum):
    """Niveles de confianza para campos detectados."""
    HIGH = "alta"       # Match exacto o formato válido
    MEDIUM = "media"    # Fuzzy match o inferido
    LOW = "baja"        # Adivinado, requiere revisión
    NONE = "ninguna"    # No detectado


@dataclass
class FieldResult:
    """Resultado de detección de un campo."""
    value: str
    confidence: Confidence
    source: str = ""  # Columna o método de origen
    notes: str = ""   # Notas adicionales


@dataclass
class GuestRecord:
    """Registro de huésped procesado."""
    row_number: int
    documento: FieldResult = None
    tipo_documento: FieldResult = None
    nombres: FieldResult = None
    primer_apellido: FieldResult = None
    segundo_apellido: FieldResult = None
    nacionalidad: FieldResult = None
    fecha_nacimiento: FieldResult = None
    fecha_movimiento: FieldResult = None
    procedencia: FieldResult = None
    destino: FieldResult = None

    is_valid: bool = False
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


class CountryCodes:
    """Base de datos de códigos de países SIRE - Lista oficial de Migración Colombia."""

    # Códigos SIRE oficiales de Migración Colombia (250 países/territorios)
    CODES = {
        # === AMÉRICA DEL NORTE ===
        "ESTADOS UNIDOS": "249", "UNITED STATES": "249", "UNITED STATES OF AMERICA": "249",
        "USA": "249", "US": "249", "AMERICA": "249", "E.E.U.U.": "249", "EEUU": "249",
        "CANADA": "149", "CANADÁ": "149", "CAN": "149",
        "MEXICO": "493", "MÉXICO": "493", "MEX": "493",
        "GROENLANDIA": "315", "GREENLAND": "315",
        "BERMUDAS": "90", "BERMUDA": "90",
        "SAN PEDRO Y MIQUELON": "682", "SAINT PIERRE AND MIQUELON": "682",

        # === CENTROAMÉRICA ===
        "GUATEMALA": "317", "GTM": "317",
        "HONDURAS": "345", "HND": "345",
        "EL SALVADOR": "242", "SLV": "242",
        "NICARAGUA": "521", "NIC": "521",
        "COSTA RICA": "196", "CRI": "196",
        "PANAMA": "580", "PANAMÁ": "580", "PAN": "580",
        "BELICE": "88", "BELIZE": "88", "BLZ": "88",

        # === CARIBE ===
        "CUBA": "199", "CUB": "199",
        "HAITI": "341", "HAITÍ": "341", "HTI": "341",
        "REPUBLICA DOMINICANA": "647", "DOMINICAN REPUBLIC": "647", "DOM": "647",
        "PUERTO RICO": "611", "PRI": "611",
        "JAMAICA": "391", "JAM": "391",
        "TRINIDAD Y TOBAGO": "815", "TRINIDAD AND TOBAGO": "815", "TTO": "815",
        "BAHAMAS": "77", "BAHAMAS ISLANDS": "77", "BHS": "77",
        "BARBADOS": "83", "BRB": "83",
        "ANTIGUA Y BARBUDA": "43", "ANTIGUA AND BARBUDA": "43", "ATG": "43",
        "DOMINICA": "235", "DMA": "235",
        "GRANADA": "297", "GRENADA": "297", "GRD": "297",
        "SAN CRISTOBAL Y NIEVES": "695", "SAINT KITTS AND NEVIS": "695", "KNA": "695",
        "SANTA LUCIA": "715", "SAINT LUCIA": "715", "LCA": "715",
        "SAN VICENTE Y LAS GRANADINAS": "705", "SAINT VINCENT AND THE GRENADINES": "705", "VCT": "705",
        "ARUBA": "67", "ABW": "67",
        "ANTILLAS HOLANDESAS": "921", "NETHERLANDS ANTILLES": "921", "ANT": "921",
        "ANTILLAS NEERLANDESAS": "44",
        "CURACAO": "201", "CURAZAO": "201",
        "ANGUILA": "895", "ANGUILLA": "895", "AIA": "895",
        "ISLAS VIRGENES BRITANICAS": "866", "BRITISH VIRGIN ISLANDS": "866", "VGB": "866",
        "ISLAS VIRGENES ESTADOUNIDENSES": "867", "US VIRGIN ISLANDS": "867", "VIR": "867",
        "ISLAS CAIMAN": "137", "CAYMAN ISLANDS": "137", "CYM": "137",
        "MONTSERRAT": "501", "MONSERRAT": "501", "MSR": "501",
        "ISLAS TURCAS Y CAICOS": "900", "TURKS AND CAICOS ISLANDS": "900", "TCA": "900",
        "GUADALUPE": "338", "GUADELOUPE": "338", "GLP": "338",
        "MARTINICA": "490", "MARTINIQUE": "490", "MTQ": "490",

        # === SUDAMÉRICA ===
        "COLOMBIA": "169", "COL": "169",
        "VENEZUELA": "850", "VEN": "850",
        "ECUADOR": "239", "ECU": "239",
        "PERU": "589", "PERÚ": "589", "PER": "589",
        "BOLIVIA": "97", "BOL": "97",
        "CHILE": "211", "CHL": "211",
        "ARGENTINA": "63", "ARG": "63",
        "URUGUAY": "845", "URY": "845",
        "PARAGUAY": "586", "PRY": "586",
        "BRASIL": "105", "BRAZIL": "105", "BRA": "105",
        "GUYANA": "325", "GUY": "325",
        "SURINAM": "770", "SURINAME": "770", "SUR": "770",
        "GUAYANA FRANCESA": "340", "FRENCH GUIANA": "340", "GUF": "340",

        # === EUROPA OCCIDENTAL ===
        "ESPANA": "245", "ESPAÑA": "245", "SPAIN": "245", "ESP": "245",
        "FRANCIA": "275", "FRANCE": "275", "FRA": "275",
        "ALEMANIA": "23", "GERMANY": "23", "DEU": "23", "GER": "23",
        "ITALIA": "386", "ITALY": "386", "ITA": "386",
        "PORTUGAL": "607", "PRT": "607",
        "REINO UNIDO": "628", "UNITED KINGDOM": "628", "UK": "628", "GBR": "628",
        "ENGLAND": "628", "GREAT BRITAIN": "628", "GRAN BRETAÑA": "628", "INGLATERRA": "628",
        "IRLANDA": "375", "IRELAND": "375", "IRL": "375", "EIRE": "375",
        "PAISES BAJOS": "573", "NETHERLANDS": "573", "HOLANDA": "573", "NLD": "573",
        "BELGICA": "87", "BÉLGICA": "87", "BELGIUM": "87", "BEL": "87",
        "LUXEMBURGO": "442", "LUXEMBOURG": "442", "LUX": "442",
        "SUIZA": "767", "SWITZERLAND": "767", "CHE": "767",
        "AUSTRIA": "72", "AUT": "72",
        "LIECHTENSTEIN": "441", "LIE": "441",
        "MONACO": "496", "MCO": "496",
        "ANDORRA": "37", "AND": "37",
        "SAN MARINO": "701", "SMR": "701",
        "CIUDAD DEL VATICANO": "717", "VATICAN": "717", "VATICANO": "717", "SANTA SEDE": "717", "VAT": "717",
        "GIBRALTAR": "293", "GIB": "293",

        # === EUROPA NÓRDICA ===
        "SUECIA": "764", "SWEDEN": "764", "SWE": "764",
        "NORUEGA": "538", "NORWAY": "538", "NOR": "538",
        "DINAMARCA": "232", "DENMARK": "232", "DNK": "232",
        "FINLANDIA": "271", "FINLAND": "271", "FIN": "271",
        "ISLANDIA": "379", "ICELAND": "379", "ISL": "379",
        "ISLAS FEROE": "390", "FAROE ISLANDS": "390", "FRO": "390",
        "ALAND": "384",
        "SVALBARD Y JAN MAYEN": "730",

        # === EUROPA ORIENTAL ===
        "RUSIA": "673", "RUSSIA": "673", "RUSSIAN FEDERATION": "673", "RUS": "673",
        "UCRANIA": "830", "UKRAINE": "830", "UKR": "830",
        "BIELORRUSIA": "85", "BELARUS": "85", "BLR": "85",
        "POLONIA": "603", "POLAND": "603", "POL": "603",
        "REPUBLICA CHECA": "207", "CZECH REPUBLIC": "207", "CZECHIA": "207", "CZE": "207",
        "ESLOVAQUIA": "247", "SLOVAKIA": "247", "SVK": "247",
        "HUNGRIA": "355", "HUNGARY": "355", "HUN": "355",
        "RUMANIA": "670", "ROMANIA": "670", "ROU": "670",
        "BULGARIA": "111", "BGR": "111",
        "MOLDAVIA": "495", "MOLDOVA": "495", "MDA": "495",

        # === EUROPA SURORIENTAL (BALCANES) ===
        "GRECIA": "301", "GREECE": "301", "GRC": "301",
        "TURQUIA": "827", "TURQUÍA": "827", "TURKEY": "827", "TUR": "827",
        "CROACIA": "198", "CROATIA": "198", "HRV": "198",
        "SERBIA": "729", "SRB": "729",
        "BOSNIA": "99", "BOSNIA HERZEGOVINA": "99", "BOSNIA AND HERZEGOVINA": "99", "BIH": "99",
        "MONTENEGRO": "499", "MNE": "499",
        "ESLOVENIA": "248", "SLOVENIA": "248", "SVN": "248",
        "MACEDONIA": "448", "ARY MACEDONIA": "448", "NORTH MACEDONIA": "448", "MKD": "448",
        "REPUBLICA DE MACEDONIA": "642",
        "ALBANIA": "17", "ALB": "17",
        "KOSOVO": "414",

        # === EUROPA BÁLTICA ===
        "LITUANIA": "429", "LITHUANIA": "429", "LTU": "429",
        "LETONIA": "428", "LATVIA": "428", "LVA": "428",
        "ESTONIA": "251", "EST": "251",

        # === CÁUCASO ===
        "GEORGIA": "287", "GEO": "287",
        "ARMENIA": "65", "ARM": "65",
        "AZERBAIYAN": "75", "AZERBAIJAN": "75", "AZE": "75",

        # === ASIA ORIENTAL ===
        "CHINA": "215", "CHN": "215",
        "JAPON": "399", "JAPÓN": "399", "JAPAN": "399", "JPN": "399",
        "COREA DEL SUR": "190", "SOUTH KOREA": "190", "KOREA": "190", "KOR": "190",
        "COREA DEL NORTE": "651", "NORTH KOREA": "651", "PRK": "651",
        "TAIWAN": "774", "TWN": "774",
        "HONG KONG": "347", "HKG": "347",
        "MACAO": "447", "MACAU": "447", "MAC": "447",
        "MONGOLIA": "497", "MNG": "497",

        # === ASIA SURORIENTAL ===
        "TAILANDIA": "776", "THAILAND": "776", "THA": "776",
        "VIETNAM": "855", "VIET NAM": "855", "VNM": "855",
        "FILIPINAS": "267", "PHILIPPINES": "267", "PHL": "267",
        "INDONESIA": "365", "IDN": "365",
        "MALASIA": "455", "MALAYSIA": "455", "MYS": "455",
        "SINGAPUR": "741", "SINGAPORE": "741", "SGP": "741",
        "MYANMAR": "507", "BIRMANIA": "507", "BURMA": "507", "MMR": "507",
        "CAMBOYA": "141", "CAMBODIA": "141", "KAMPUCHEA": "141", "KHM": "141",
        "LAOS": "420", "LAO": "420",
        "BRUNEI": "108", "BRUNEI DARUSSALAM": "108", "BRN": "108",
        "TIMOR ORIENTAL": "783", "EAST TIMOR": "783", "TIMOR LESTE": "783", "TLS": "783",

        # === ASIA MERIDIONAL ===
        "INDIA": "361", "IND": "361",
        "PAKISTAN": "576", "PAK": "576",
        "BANGLADESH": "81", "BGD": "81",
        "SRI LANKA": "750", "LKA": "750", "CEILAN": "750",
        "NEPAL": "517", "NPL": "517",
        "BUTAN": "117", "BHUTAN": "117", "BTN": "117",
        "MALDIVAS": "461", "MALDIVES": "461", "MDV": "461",
        "AFGANISTAN": "13", "AFGHANISTAN": "13", "AFG": "13",

        # === ASIA CENTRAL ===
        "KAZAJISTAN": "406", "KAZAKHSTAN": "406", "KAZ": "406",
        "UZBEKISTAN": "847", "UZB": "847",
        "TURKMENISTAN": "829", "TKM": "829",
        "KIRGUISTAN": "412", "KYRGYZSTAN": "412", "KGZ": "412",
        "TAYIKISTAN": "775", "TAJIKISTAN": "775", "TJK": "775",

        # === MEDIO ORIENTE ===
        "ISRAEL": "383", "ISR": "383",
        "PALESTINA": "600", "PALESTINE": "600", "PSE": "600",
        "LIBANO": "431", "LEBANON": "431", "LBN": "431",
        "SIRIA": "744", "SYRIA": "744", "SYR": "744",
        "JORDANIA": "403", "JORDAN": "403", "JOR": "403",
        "IRAQ": "369", "IRQ": "369", "IRAK": "369",
        "IRAN": "372", "IRN": "372",
        "ARABIA SAUDITA": "55", "SAUDI ARABIA": "55", "SAU": "55",
        "EMIRATOS ARABES UNIDOS": "244", "UNITED ARAB EMIRATES": "244", "UAE": "244", "ARE": "244",
        "KUWAIT": "413", "KWT": "413",
        "QATAR": "618", "QAT": "618",
        "BAHREIN": "80", "BAHRAIN": "80", "BHR": "80",
        "OMAN": "542", "OMN": "542",
        "YEMEN": "880", "YEM": "880",
        "CHIPRE": "221", "CYPRUS": "221", "CYP": "221",

        # === OCEANÍA ===
        "AUSTRALIA": "69", "AUS": "69",
        "NUEVA ZELANDA": "540", "NEW ZEALAND": "540", "NZL": "540",
        "PAPUA NUEVA GUINEA": "582", "PAPUA NEW GUINEA": "582", "PNG": "582",
        "FIYI": "255", "FIJI": "255", "FJI": "255",
        "ISLAS SALOMON": "395", "SOLOMON ISLANDS": "395", "SLB": "395",
        "VANUATU": "849", "VUT": "849",
        "SAMOA": "699", "WSM": "699",
        "SAMOA AMERICANA": "698", "AMERICAN SAMOA": "698", "ASM": "698",
        "TONGA": "810", "TON": "810",
        "KIRIBATI": "411", "KIR": "411",
        "TUVALU": "828", "TUV": "828",
        "NAURU": "508", "NRU": "508",
        "PALAOS": "578", "PALAU": "578", "PLW": "578",
        "MICRONESIA": "503", "FSM": "503",
        "ISLAS MARSHALL": "475", "MARSHALL ISLANDS": "475", "MHL": "475",
        "GUAM": "339", "GUM": "339",
        "ISLAS MARIANAS DEL NORTE": "392", "NORTHERN MARIANA ISLANDS": "392", "MNP": "392",
        "NUEVA CALEDONIA": "539", "NEW CALEDONIA": "539", "NCL": "539",
        "POLINESIA FRANCESA": "609", "FRENCH POLYNESIA": "609", "PYF": "609",
        "WALLIS Y FUTUNA": "394", "WALLIS AND FUTUNA": "394", "WLF": "394",
        "ISLAS COOK": "388", "COOK ISLANDS": "388", "COK": "388",
        "NIUE": "531", "NIU": "531",
        "TOKELAU": "812", "TKL": "812",
        "ISLAS PITCAIRN": "381", "PITCAIRN": "381", "PCN": "381",
        "NORFOLK": "163", "NORFOLK ISLAND": "163", "NFK": "163",
        "ISLAS COCOS": "178", "COCOS KEELING ISLANDS": "178", "CCK": "178",
        "ISLA DE NAVIDAD": "387", "CHRISTMAS ISLAND": "387", "CXR": "387",

        # === ÁFRICA DEL NORTE ===
        "EGIPTO": "240", "EGYPT": "240", "EGY": "240",
        "LIBIA": "438", "LIBYA": "438", "LBY": "438",
        "TUNEZ": "820", "TUNISIA": "820", "TUN": "820",
        "ARGELIA": "59", "ALGERIA": "59", "DZA": "59",
        "MARRUECOS": "474", "MOROCCO": "474", "MAR": "474",
        "SAHARA OCCIDENTAL": "680", "WESTERN SAHARA": "680", "ESH": "680",
        "SUDAN": "759", "SDN": "759",

        # === ÁFRICA OCCIDENTAL ===
        "NIGERIA": "525", "NGA": "525",
        "NIGER": "528", "NER": "528",
        "GHANA": "289", "GHA": "289",
        "COSTA DE MARFIL": "193", "COTE D'IVOIRE": "193", "IVORY COAST": "193", "CIV": "193",
        "SENEGAL": "728", "SEN": "728",
        "MALI": "464", "MLI": "464",
        "BURKINA FASO": "113", "BFA": "113",
        "GUINEA": "329", "GIN": "329",
        "GUINEA BISSAU": "334", "GUINEA-BISSAU": "334", "GNB": "334",
        "SIERRA LEONA": "735", "SIERRA LEONE": "735", "SLE": "735",
        "LIBERIA": "434", "LBR": "434",
        "TOGO": "800", "TGO": "800",
        "BENIN": "89", "BEN": "89",
        "MAURITANIA": "488", "MRT": "488",
        "CABO VERDE": "127", "CAPE VERDE": "127", "CPV": "127",
        "GAMBIA": "285", "GMB": "285",

        # === ÁFRICA CENTRAL ===
        "CAMERUN": "145", "CAMEROON": "145", "CMR": "145",
        "REPUBLICA CENTROAFRICANA": "998", "CENTRAL AFRICAN REPUBLIC": "998", "CAF": "998",
        "CHAD": "151", "TCD": "151",
        "REPUBLICA DEL CONGO": "170", "CONGO": "170", "COG": "170",
        "REPUBLICA DEMOCRATICA DEL CONGO": "177", "ZAIRE": "177", "COD": "177",
        "GUINEA ECUATORIAL": "331", "EQUATORIAL GUINEA": "331", "GNQ": "331",
        "GABON": "281", "GAB": "281",
        "SANTO TOME Y PRINCIPE": "720", "SAO TOME AND PRINCIPE": "720", "STP": "720",
        "ANGOLA": "40", "AGO": "40",

        # === ÁFRICA ORIENTAL ===
        "KENIA": "410", "KENYA": "410", "KEN": "410",
        "ETIOPIA": "253", "ETHIOPIA": "253", "ETH": "253",
        "TANZANIA": "780", "TZA": "780",
        "UGANDA": "833", "UGA": "833",
        "RWANDA": "675", "RUANDA": "675", "RWA": "675",
        "BURUNDI": "115", "BDI": "115",
        "SOMALIA": "748", "SOM": "748",
        "YIBUTI": "920", "DJIBOUTI": "920", "DJI": "920",
        "ERITREA": "246", "ERI": "246",
        "SEYCHELLES": "731", "SYC": "731",
        "MAURICIO": "485", "MAURITIUS": "485", "MUS": "485",
        "COMORAS": "171", "COMOROS": "171", "COM": "171",
        "MADAGASCAR": "450", "MDG": "450",
        "REUNION": "650", "REU": "650",
        "MAYOTTE": "494",

        # === ÁFRICA AUSTRAL ===
        "SUDAFRICA": "756", "SUDÁFRICA": "756", "SOUTH AFRICA": "756", "ZAF": "756",
        "NAMIBIA": "512", "NAM": "512",
        "BOTSWANA": "101", "BWA": "101",
        "ZIMBABUE": "892", "ZIMBABWE": "892", "ZWE": "892",
        "ZAMBIA": "890", "ZMB": "890",
        "MOZAMBIQUE": "505", "MOZ": "505",
        "MALAWI": "458", "MWI": "458",
        "LESOTHO": "426", "LSO": "426",
        "SWAZILANDIA": "773", "ESWATINI": "773", "SWAZILAND": "773", "SWZ": "773",

        # === TERRITORIOS Y OTROS ===
        "ISLAS ULTRAMARINAS DE ESTADOS UNIDOS": "200",
        "TERRITORIO BRITANICO DEL OCEANO INDICO": "779", "BRITISH INDIAN OCEAN TERRITORY": "779", "IOT": "779",
        "SANTA HELENA": "708", "SAINT HELENA": "708", "SHN": "708",
        "ISLA DE MAN": "380", "ISLE OF MAN": "380", "IMN": "380",
        "JERSEY": "160", "JEY": "160",
        "GUERNSEY": "146", "GGY": "146",
        "ANTARTIDA": "143", "ANTARCTICA": "143", "ATA": "143",
        "ISLA BOUVET": "173", "BOUVET ISLAND": "173",
        "ISLAS HEARD Y MCDONALD": "186",
        "ISLAS MALVINAS": "191", "FALKLAND ISLANDS": "191", "FLK": "191",
        "TERRITORIOS AUSTRALES FRANCESES": "781",

        # === ORGANIZACIONES INTERNACIONALES ===
        "INTERPOL": "980",
        "NACIONES UNIDAS": "981",
        "NO APLICA": "0",
    }

    @classmethod
    def get_code(cls, country: str) -> Tuple[str, Confidence]:
        """
        Obtiene el código SIRE de un país.

        Returns:
            Tuple[código, nivel_confianza]
        """
        if not country or is_nan_or_empty(country):
            return "", Confidence.NONE

        normalized = str(country).upper().strip()
        normalized = re.sub(r'[^A-ZÁÉÍÓÚÑÜ\s]', '', normalized)
        normalized = re.sub(r'\s+', ' ', normalized).strip()

        # Match exacto
        if normalized in cls.CODES:
            return cls.CODES[normalized], Confidence.HIGH

        # Buscar coincidencia parcial
        for key, code in cls.CODES.items():
            if normalized in key or key in normalized:
                return code, Confidence.MEDIUM

        # Fuzzy matching: buscar palabras clave
        words = normalized.split()
        for word in words:
            if len(word) >= 3:
                for key, code in cls.CODES.items():
                    if word in key:
                        return code, Confidence.LOW

        return "", Confidence.NONE

    @classmethod
    def is_colombia(cls, country: str) -> bool:
        """Verifica si el país es Colombia."""
        code, _ = cls.get_code(country)
        return code == "169"


class ColombianCities:
    """Base de datos de ciudades colombianas para detectar destinos locales."""

    # Ciudades principales de Colombia (las más comunes en turismo)
    CITIES = {
        # Capitales de departamento y ciudades principales
        "MEDELLIN": "5001", "MEDELLÍN": "5001",
        "BOGOTA": "11001", "BOGOTÁ": "11001", "SANTA FE DE BOGOTA": "11001",
        "CALI": "76001", "SANTIAGO DE CALI": "76001",
        "BARRANQUILLA": "8001",
        "CARTAGENA": "13001", "CARTAGENA DE INDIAS": "13001",
        "SANTA MARTA": "47001",
        "BUCARAMANGA": "68001",
        "PEREIRA": "66001",
        "MANIZALES": "17001",
        "CUCUTA": "54001", "CÚCUTA": "54001",
        "IBAGUE": "73001", "IBAGUÉ": "73001",
        "VILLAVICENCIO": "50001",
        "PASTO": "52001", "SAN JUAN DE PASTO": "52001",
        "MONTERIA": "23001", "MONTERÍA": "23001",
        "NEIVA": "41001",
        "ARMENIA": "63001",
        "VALLEDUPAR": "20001",
        "POPAYAN": "19001", "POPAYÁN": "19001",
        "SINCELEJO": "70001",
        "TUNJA": "15001",
        "RIOHACHA": "44001",
        "QUIBDO": "27001", "QUIBDÓ": "27001",
        "FLORENCIA": "18001",
        "YOPAL": "85001",
        "MOCOA": "86001",
        "LETICIA": "91001",
        "ARAUCA": "81001",
        "INIRIDA": "94001", "INÍRIDA": "94001",
        "MITU": "97001", "MITÚ": "97001",
        "PUERTO CARRENO": "99001", "PUERTO CARREÑO": "99001",
        "SAN JOSE DEL GUAVIARE": "95001", "SAN JOSÉ DEL GUAVIARE": "95001",

        # Ciudades turísticas importantes
        "SAN ANDRES": "88001", "SAN ANDRÉS": "88001", "SAN ANDRES ISLA": "88001",
        "PROVIDENCIA": "88564",
        "BUGA": "76111", "GUADALAJARA DE BUGA": "76111",
        "BUENAVENTURA": "76109",
        "BARICHARA": "68079",
        "VILLA DE LEYVA": "15407",
        "GUATAPE": "5321", "GUATAPÉ": "5321",
        "JARDIN": "5364", "JARDÍN": "5364",
        "SALENTO": "63690",
        "FILANDIA": "63272",
        "SANTA FE DE ANTIOQUIA": "5042", "SANTAFE DE ANTIOQUIA": "5042",
        "RIONEGRO": "5615",
        "ENVIGADO": "5266",
        "ITAGUI": "5360", "ITAGÜÍ": "5360",
        "BELLO": "5088",
        "SABANETA": "5631",
        "LA CEJA": "5376",
        "MARINILLA": "5440",
        "EL RETIRO": "5607", "RETIRO": "5607",
        "GIRARDOTA": "5308",
        "COPACABANA": "5212",
        "ZIPAQUIRA": "25899", "ZIPAQUIRÁ": "25899",
        "CHIA": "25175", "CHÍA": "25175",
        "CAJICA": "25126", "CAJICÁ": "25126",
        "SOACHA": "25754",
        "GIRARDOT": "25307",
        "MELGAR": "73449",
        "VILLETA": "25873",
        "LA MESA": "25386",
        "FUSAGASUGA": "25290", "FUSAGASUGÁ": "25290",
        "PALMIRA": "76520",
        "TULUA": "76834", "TULUÁ": "76834",
        "CARTAGO": "76147",
        "JAMUNDI": "76364", "JAMUNDÍ": "76364",
        "YUMBO": "76892",
        "SOLEDAD": "8758",
        "MALAMBO": "8433",
        "TURBACO": "13836",
        "MAGANGUE": "13430", "MAGANGUÉ": "13430",
        "LORICA": "23417",
        "CERETE": "23162", "CERETÉ": "23162",
        "SOGAMOSO": "15759",
        "DUITAMA": "15238",
        "PAIPA": "15516",
        "IPIALES": "52356",
        "TUMACO": "52835",

        # También aceptar "COLOMBIA" como destino
        "COLOMBIA": "169",
    }

    @classmethod
    def is_colombian_city(cls, text: str) -> Tuple[bool, str]:
        """
        Verifica si el texto es una ciudad colombiana.

        Returns:
            Tuple[es_ciudad_colombiana, código_ciudad]
        """
        if not text or is_nan_or_empty(text):
            return False, ""

        normalized = str(text).upper().strip()
        normalized = re.sub(r'[^A-ZÁÉÍÓÚÑÜ\s]', '', normalized)
        normalized = re.sub(r'\s+', ' ', normalized).strip()

        # Match exacto
        if normalized in cls.CITIES:
            return True, cls.CITIES[normalized]

        # Buscar coincidencia parcial solo si el texto es suficientemente largo
        # para evitar falsos positivos como "USA" en "FUSAGASUGA"
        if len(normalized) >= 5:
            for city, code in cls.CITIES.items():
                # Solo si el texto está contenido en la ciudad (no al revés)
                # y representa una porción significativa
                if city in normalized:
                    return True, code

        return False, ""

    @classmethod
    def get_colombia_code_if_city(cls, text: str) -> Tuple[str, Confidence]:
        """
        Si el texto es una ciudad colombiana, retorna el código de Colombia.
        Útil para el campo destino.

        Returns:
            Tuple[código_país, confianza] - "169" si es ciudad colombiana
        """
        is_city, _ = cls.is_colombian_city(text)
        if is_city:
            return "169", Confidence.HIGH
        return "", Confidence.NONE


class DocumentTypes:
    """Tipos de documento SIRE."""

    CODES = {
        "PASAPORTE": "3", "PASSPORT": "3", "PAS": "3", "PP": "3",
        "CEDULA DE EXTRANJERIA": "5", "CEDULA EXTRANJERIA": "5", "CE": "5",
        "CARNE DIPLOMATICO": "46", "DIPLOMATIC": "46", "DIPLOMATICO": "46",
        "DOCUMENTO EXTRANJERO": "10", "FOREIGN DOCUMENT": "10",
        "PPT": "52", "PERMISO PROTECCION TEMPORAL": "52",
        "VISA": "10",
        "DNI": "3",  # Documento Nacional de Identidad -> tratar como pasaporte para extranjeros
        "ID": "3",
        "NATIONAL ID": "3",
    }

    @classmethod
    def get_code(cls, doc_type: str) -> Tuple[str, Confidence]:
        """Obtiene el código SIRE del tipo de documento."""
        if not doc_type or is_nan_or_empty(doc_type):
            return "3", Confidence.LOW  # Default: Pasaporte

        normalized = str(doc_type).upper().strip()

        # Match exacto
        for key, code in cls.CODES.items():
            if key in normalized or normalized in key:
                return code, Confidence.HIGH

        # Default basado en palabras clave
        if any(word in normalized for word in ["PASAP", "PASSPO", "PP"]):
            return "3", Confidence.MEDIUM
        if any(word in normalized for word in ["CEDULA", "CE", "EXTRAN"]):
            return "5", Confidence.MEDIUM
        if any(word in normalized for word in ["DIPLOM", "CARNE"]):
            return "46", Confidence.MEDIUM
        if any(word in normalized for word in ["PPT", "PROTEC", "TEMPORAL"]):
            return "52", Confidence.MEDIUM

        return "3", Confidence.LOW  # Default: Pasaporte


class ColumnDetector:
    """Detector inteligente de columnas."""

    # Patrones para cada tipo de campo
    # IMPORTANTE: El orden importa - tipo_documento debe detectarse antes que numero_documento
    FIELD_PATTERNS = {
        'tipo_documento': {
            'names': [
                'tipo de documento', 'document type', 'tipo documento',
                'doc type', 'id type', 'tipo de id', 'tipo id'
            ],
            'content_patterns': [
                r'pasaporte|passport|cedula|dni|visa|ppt',
            ],
            'priority': 1,  # Alta prioridad - detectar primero
        },
        'numero_documento': {
            'names': [
                'document number', 'numero documento', 'número de documento',
                'numero de identificacion', 'número de identificación',
                'passport number', 'passport no', 'id number',
                'doc number', 'document no', 'numero del documento',
                'número del documento', 'no. documento', 'nro documento',
                'n documento', 'num documento', 'numero id', 'no identificacion',
                'número identificación'
            ],
            'content_patterns': [
                r'^[A-Z]{1,2}\d{6,9}$',      # Pasaporte típico
                r'^\d{8,12}$',               # Número solo dígitos
                r'^[A-Z0-9]{6,12}$',         # Alfanumérico
            ],
            'exclude_patterns': [r'^\d{1,5}$'],  # Muy corto, probablemente no es documento
            'exclude_column_keywords': ['tipo'],  # NO matchear columnas que contengan "tipo"
            'priority': 2,  # Menor prioridad - detectar después de tipo_documento
        },
        'nombres': {
            'names': [
                'name', 'first name', 'nombres', 'given name', 'firstname',
                'given names', 'nombre', 'primer nombre'
            ],
        },
        'primer_apellido': {
            'names': [
                'surname', 'last name', 'apellido', 'primer apellido',
                'family name', 'lastname', 'apellidos'
            ],
        },
        'nombre_completo': {
            'names': [
                'guest name', 'nombre completo', 'full name', 'guest',
                'huesped', 'nombre y apellido', 'huésped', 'cliente'
            ],
        },
        'nacionalidad': {
            'names': [
                'country', 'nationality', 'nacionalidad', 'pais', 'país',
                'citizen', 'citizenship', 'nation'
            ],
        },
        'fecha_nacimiento': {
            'names': [
                'birthday', 'birth date', 'fecha nacimiento', 'date of birth',
                'birthdate', 'dob', 'nacimiento', 'born', 'cumpleaños',
                'fecha de nacimiento', 'f. nacimiento'
            ],
            'content_patterns': [
                r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}',
                r'\d{4}[/-]\d{1,2}[/-]\d{1,2}',
            ],
        },
        'fecha_checkin': {
            'names': [
                'arrival date', 'arrival', 'check-in', 'checkin', 'check in',
                'llegada', 'entrada', 'fecha entrada', 'fecha llegada',
                'fecha de llegada', 'ingreso'
            ],
        },
        'fecha_checkout': {
            'names': [
                'departure date', 'departure', 'check-out', 'checkout',
                'check out', 'salida', 'fecha salida', 'fecha checkout',
                'fecha de salida', 'egreso'
            ],
        },
        'procedencia': {
            'names': [
                'pais de procedencia', 'country of origin', 'origin country',
                'procedencia', 'from', 'origen', 'viene de'
            ],
        },
        'destino': {
            'names': [
                'pais de destino', 'destination country', 'destino',
                'destination', 'to', 'va a', 'hacia'
            ],
        },
    }

    @classmethod
    def _similarity(cls, s1: str, s2: str) -> float:
        """Calcula similitud entre dos strings (0-1)."""
        s1, s2 = s1.lower(), s2.lower()
        if s1 == s2:
            return 1.0

        # Similitud por palabras comunes
        words1 = set(s1.split())
        words2 = set(s2.split())

        if not words1 or not words2:
            return 0.0

        common = words1 & words2
        return len(common) / max(len(words1), len(words2))

    @classmethod
    def _fuzzy_match(cls, column: str, patterns: List[str], threshold: float = 0.5) -> Tuple[bool, float]:
        """
        Verifica si una columna coincide con algún patrón usando fuzzy matching.

        Returns:
            Tuple[coincide, puntuación]
        """
        col_lower = column.lower().strip()
        best_score = 0.0

        for pattern in patterns:
            # Match exacto
            if col_lower == pattern:
                return True, 1.0

            # Contiene exactamente
            if pattern in col_lower or col_lower in pattern:
                score = len(pattern) / max(len(col_lower), len(pattern))
                best_score = max(best_score, score + 0.3)

            # Similitud por palabras
            similarity = cls._similarity(col_lower, pattern)
            best_score = max(best_score, similarity)

        return best_score >= threshold, best_score

    @classmethod
    def _should_exclude_column(cls, column: str, config: dict) -> bool:
        """Verifica si una columna debe ser excluida según las palabras clave de exclusión."""
        exclude_keywords = config.get('exclude_column_keywords', [])
        col_lower = column.lower()

        for keyword in exclude_keywords:
            if keyword.lower() in col_lower:
                return True
        return False

    @classmethod
    def detect_columns(cls, df: pd.DataFrame) -> Dict[str, Tuple[str, Confidence]]:
        """
        Detecta qué columna corresponde a cada campo SIRE.

        Returns:
            Dict[campo_sire -> (columna, confianza)]
        """
        detected = {}
        used_columns = set()
        columns = list(df.columns)

        # Ordenar campos por prioridad (menor número = mayor prioridad)
        sorted_fields = sorted(
            cls.FIELD_PATTERNS.items(),
            key=lambda x: x[1].get('priority', 99)
        )

        # Primera pasada: matches de alta confianza
        for field, config in sorted_fields:
            for col in columns:
                if col in used_columns:
                    continue

                # Verificar exclusiones
                if cls._should_exclude_column(col, config):
                    continue

                matches, score = cls._fuzzy_match(col, config['names'])

                if score >= 0.8:  # Alta confianza
                    detected[field] = (col, Confidence.HIGH)
                    used_columns.add(col)
                    break

        # Segunda pasada: matches de media confianza
        for field, config in sorted_fields:
            if field in detected:
                continue

            for col in columns:
                if col in used_columns:
                    continue

                # Verificar exclusiones
                if cls._should_exclude_column(col, config):
                    continue

                matches, score = cls._fuzzy_match(col, config['names'], threshold=0.4)

                if matches:
                    detected[field] = (col, Confidence.MEDIUM)
                    used_columns.add(col)
                    break

        # Tercera pasada: análisis de contenido para campos críticos no detectados
        critical_fields = ['numero_documento', 'fecha_nacimiento', 'nacionalidad']

        for field in critical_fields:
            if field in detected:
                continue

            config = cls.FIELD_PATTERNS.get(field, {})
            content_patterns = config.get('content_patterns', [])

            if not content_patterns:
                continue

            for col in columns:
                if col in used_columns:
                    continue

                # Verificar exclusiones
                if cls._should_exclude_column(col, config):
                    continue

                # Analizar contenido de la columna
                sample = df[col].dropna().head(10).astype(str)
                matches = 0

                for value in sample:
                    for pattern in content_patterns:
                        if re.match(pattern, value.strip(), re.IGNORECASE):
                            matches += 1
                            break

                # Si >50% de la muestra coincide, probablemente es este campo
                if matches >= len(sample) * 0.5:
                    detected[field] = (col, Confidence.LOW)
                    used_columns.add(col)
                    logger.info(f"Campo '{field}' detectado por contenido en columna '{col}'")
                    break

        return detected


class DateParser:
    """Parser inteligente de fechas."""

    FORMATS = [
        "%d/%m/%Y",      # 31/12/2024
        "%Y-%m-%d",      # 2024-12-31
        "%d-%m-%Y",      # 31-12-2024
        "%m/%d/%Y",      # 12/31/2024 (formato US)
        "%d.%m.%Y",      # 31.12.2024
        "%Y/%m/%d",      # 2024/12/31
        "%d %b %Y",      # 31 Dec 2024
        "%d %B %Y",      # 31 December 2024
    ]

    @classmethod
    def parse(cls, date_val: Any) -> Tuple[str, Confidence]:
        """
        Parsea una fecha a formato SIRE (dd/mm/yyyy).

        Returns:
            Tuple[fecha_formateada, confianza]
        """
        if date_val is None or is_nan_or_empty(date_val):
            return "", Confidence.NONE

        # Si es Timestamp de pandas
        if hasattr(date_val, 'strftime'):
            return date_val.strftime('%d/%m/%Y'), Confidence.HIGH

        date_str = str(date_val).strip()
        if not date_str or date_str.lower() in ['nan', 'none', 'nat', '']:
            return "", Confidence.NONE

        # Remover hora si existe
        date_str = date_str.split()[0] if ' ' in date_str else date_str

        # Intentar cada formato
        for fmt in cls.FORMATS:
            try:
                parsed = datetime.strptime(date_str, fmt)

                # Validar que la fecha sea razonable
                if 1900 <= parsed.year <= datetime.now().year + 1:
                    confidence = Confidence.HIGH if fmt in ["%d/%m/%Y", "%Y-%m-%d"] else Confidence.MEDIUM
                    return parsed.strftime('%d/%m/%Y'), confidence
            except ValueError:
                continue

        return "", Confidence.LOW

    @classmethod
    def infer_from_age(cls, age: int) -> Tuple[str, Confidence]:
        """Infiere fecha de nacimiento aproximada desde edad."""
        if not isinstance(age, (int, float)) or age < 0 or age > 120:
            return "", Confidence.NONE

        # Calcular fecha aproximada (asumiendo cumpleaños a mitad de año)
        birth_year = datetime.now().year - int(age)
        birth_date = datetime(birth_year, 6, 15)

        return birth_date.strftime('%d/%m/%Y'), Confidence.LOW


class TextNormalizer:
    """Normalizador de texto para nombres y apellidos."""

    @classmethod
    def normalize_name(cls, text: Any) -> str:
        """Normaliza un nombre o apellido."""
        if not text or is_nan_or_empty(text):
            return ""

        text = str(text)

        # Remover números y caracteres especiales, mantener acentos
        normalized = re.sub(r'[^a-zA-ZÀ-ÿ\s\-\']', '', text)
        normalized = re.sub(r'\s+', ' ', normalized).strip()

        return normalized.upper()

    @classmethod
    def split_full_name(cls, full_name: str) -> Tuple[str, str, str]:
        """
        Divide un nombre completo en componentes.

        Returns:
            Tuple[primer_apellido, segundo_apellido, nombres]
        """
        if not full_name or is_nan_or_empty(full_name):
            return "", "", ""

        parts = cls.normalize_name(full_name).split()

        if len(parts) == 0:
            return "", "", ""
        elif len(parts) == 1:
            return parts[0], "", ""
        elif len(parts) == 2:
            # Asumimos: Nombre Apellido
            return parts[1], "", parts[0]
        elif len(parts) == 3:
            # Asumimos: Nombre Apellido1 Apellido2 o Nombre1 Nombre2 Apellido
            # Heurística: si el último parece apellido común...
            return parts[-1], "", " ".join(parts[:-1])
        else:
            # 4+ partes: Asumimos Nombres... Apellido1 Apellido2
            return parts[-2], parts[-1], " ".join(parts[:-2])


class InferenceEngine:
    """Motor de inferencia para campos faltantes."""

    @classmethod
    def infer_nationality_from_origin(cls, procedencia: str) -> Tuple[str, Confidence]:
        """Infiere nacionalidad desde país de procedencia."""
        code, conf = CountryCodes.get_code(procedencia)
        if code:
            # Reducir confianza ya que es inferido
            new_conf = Confidence.MEDIUM if conf == Confidence.HIGH else Confidence.LOW
            return code, new_conf
        return "", Confidence.NONE

    @classmethod
    def infer_origin_from_nationality(cls, nacionalidad: str) -> Tuple[str, Confidence]:
        """Infiere procedencia desde nacionalidad."""
        code, conf = CountryCodes.get_code(nacionalidad)
        if code:
            new_conf = Confidence.MEDIUM if conf == Confidence.HIGH else Confidence.LOW
            return code, new_conf
        return "", Confidence.NONE

    @classmethod
    def infer_names_from_email(cls, email: str) -> Tuple[str, str, Confidence]:
        """
        Intenta extraer nombres de un email.
        Ej: john.smith@mail.com -> JOHN, SMITH
        """
        if not email or '@' not in str(email):
            return "", "", Confidence.NONE

        local_part = str(email).split('@')[0].lower()

        # Patrones comunes
        patterns = [
            r'^([a-z]+)\.([a-z]+)$',      # john.smith
            r'^([a-z]+)_([a-z]+)$',       # john_smith
            r'^([a-z]+)-([a-z]+)$',       # john-smith
            r'^([a-z]+)([A-Z][a-z]+)$',   # johnSmith
        ]

        for pattern in patterns:
            match = re.match(pattern, local_part)
            if match:
                nombre = match.group(1).upper()
                apellido = match.group(2).upper()
                return nombre, apellido, Confidence.LOW

        return "", "", Confidence.NONE


class DocumentValidator:
    """Validador de documentos."""

    # Patrones de pasaportes por país (simplificado)
    PASSPORT_PATTERNS = {
        "USA": r'^[A-Z]?\d{8,9}$',
        "DEFAULT": r'^[A-Z0-9]{6,12}$',
    }

    @classmethod
    def validate_document(cls, doc_number: str, doc_type: str = "3") -> Tuple[bool, str]:
        """
        Valida un número de documento.

        Returns:
            Tuple[es_válido, mensaje]
        """
        if not doc_number:
            return False, "Documento vacío"

        doc_number = str(doc_number).strip().upper()

        # Validaciones básicas
        if len(doc_number) < 5:
            return False, "Documento muy corto"

        if len(doc_number) > 20:
            return False, "Documento muy largo"

        if doc_number in ['NAN', 'NONE', 'NULL', 'N/A', '-']:
            return False, "Documento inválido"

        # Solo números repetidos
        if len(set(doc_number.replace('-', ''))) == 1:
            return False, "Documento con patrón inválido"

        return True, "OK"


class SireConverter:
    """Conversor principal de Police Report a formato SIRE."""

    def __init__(self, hotel_code: str, city_code: str = "5001"):
        """
        Inicializa el conversor.

        Args:
            hotel_code: Código del establecimiento SIRE
            city_code: Código de ciudad SIRE (default: 5001 = Medellín)
        """
        self.hotel_code = hotel_code
        self.city_code = city_code
        self.column_map = {}
        self.stats = {
            "total": 0,
            "valid": 0,
            "skipped": 0,
            "colombianos": 0,
            "duplicados": 0,
            "inferidos": 0,
        }
        self.errors = []
        self.warnings = []

    def read_file(self, file_path: str) -> pd.DataFrame:
        """Lee archivo de entrada."""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Archivo no encontrado: {file_path}")

        ext = os.path.splitext(file_path)[1].lower()

        if ext in ['.xlsx', '.xls']:
            df = pd.read_excel(file_path)
        elif ext == '.txt':
            # Detectar delimitador
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                first_line = f.readline()

            if '\t' in first_line:
                df = pd.read_csv(file_path, sep='\t', encoding='utf-8', on_bad_lines='skip')
            elif ';' in first_line:
                df = pd.read_csv(file_path, sep=';', encoding='utf-8', on_bad_lines='skip')
            else:
                df = pd.read_csv(file_path, encoding='utf-8', on_bad_lines='skip')
        elif ext == '.csv':
            df = pd.read_csv(file_path, encoding='utf-8', on_bad_lines='skip')
        else:
            raise ValueError(f"Formato no soportado: {ext}. Use .xlsx, .xls, .csv o .txt")

        logger.info(f"Archivo leído: {len(df)} registros, {len(df.columns)} columnas")
        return df

    def _get_value(self, row: pd.Series, field: str) -> Any:
        """Obtiene el valor de un campo desde el row."""
        if field not in self.column_map:
            return None

        col, _ = self.column_map[field]
        return row.get(col)

    def _process_guest(self, row: pd.Series, idx: int, movement_type: str) -> Optional[GuestRecord]:
        """Procesa un huésped individual."""
        guest = GuestRecord(row_number=idx + 2)  # +2 por header y 0-index

        # === DOCUMENTO ===
        doc_val = self._get_value(row, 'numero_documento')
        doc_str = str(doc_val).strip() if doc_val else ""

        if doc_str.lower() in ['nan', 'none', '', 'null']:
            doc_str = ""

        is_valid_doc, doc_msg = DocumentValidator.validate_document(doc_str)

        if not is_valid_doc:
            guest.errors.append(f"Documento: {doc_msg}")
            return guest

        guest.documento = FieldResult(doc_str, Confidence.HIGH, "numero_documento")

        # === TIPO DOCUMENTO ===
        tipo_val = self._get_value(row, 'tipo_documento')
        tipo_code, tipo_conf = DocumentTypes.get_code(tipo_val)
        guest.tipo_documento = FieldResult(tipo_code, tipo_conf, "tipo_documento")

        # === NOMBRES Y APELLIDOS ===
        if 'primer_apellido' in self.column_map:
            apellido_raw = str(self._get_value(row, 'primer_apellido') or "")
            apellido_parts = apellido_raw.strip().split()

            if len(apellido_parts) >= 2:
                primer_ap = TextNormalizer.normalize_name(apellido_parts[0])
                segundo_ap = TextNormalizer.normalize_name(" ".join(apellido_parts[1:]))
            else:
                primer_ap = TextNormalizer.normalize_name(apellido_raw)
                segundo_ap = ""

            guest.primer_apellido = FieldResult(primer_ap, Confidence.HIGH, "primer_apellido")
            guest.segundo_apellido = FieldResult(segundo_ap, Confidence.HIGH if segundo_ap else Confidence.NONE)

        if 'nombres' in self.column_map:
            nombres = TextNormalizer.normalize_name(self._get_value(row, 'nombres'))
            guest.nombres = FieldResult(nombres, Confidence.HIGH, "nombres")
        elif 'nombre_completo' in self.column_map and not guest.primer_apellido:
            full_name = self._get_value(row, 'nombre_completo')
            primer_ap, segundo_ap, nombres = TextNormalizer.split_full_name(full_name)

            guest.primer_apellido = FieldResult(primer_ap, Confidence.MEDIUM, "nombre_completo (inferido)")
            guest.segundo_apellido = FieldResult(segundo_ap, Confidence.MEDIUM)
            guest.nombres = FieldResult(nombres, Confidence.MEDIUM, "nombre_completo (inferido)")
            self.stats["inferidos"] += 1

        # === NACIONALIDAD ===
        nac_val = self._get_value(row, 'nacionalidad')
        nac_code, nac_conf = CountryCodes.get_code(nac_val)

        # Inferir desde procedencia si no hay nacionalidad
        if not nac_code and 'procedencia' in self.column_map:
            proc_val = self._get_value(row, 'procedencia')
            nac_code, nac_conf = InferenceEngine.infer_nationality_from_origin(proc_val)
            if nac_code:
                guest.warnings.append("Nacionalidad inferida desde procedencia")
                self.stats["inferidos"] += 1

        if nac_code == "169":  # Colombia
            return None  # Marcador para saltar colombianos

        guest.nacionalidad = FieldResult(nac_code, nac_conf, "nacionalidad")

        # === FECHAS ===
        if movement_type == "E":
            fecha_mov_val = self._get_value(row, 'fecha_checkin')
        else:
            fecha_mov_val = self._get_value(row, 'fecha_checkout')

        fecha_mov, fecha_mov_conf = DateParser.parse(fecha_mov_val)
        guest.fecha_movimiento = FieldResult(fecha_mov, fecha_mov_conf)

        fecha_nac_val = self._get_value(row, 'fecha_nacimiento')
        fecha_nac, fecha_nac_conf = DateParser.parse(fecha_nac_val)
        guest.fecha_nacimiento = FieldResult(fecha_nac, fecha_nac_conf)

        # === PROCEDENCIA ===
        proc_val = self._get_value(row, 'procedencia')
        proc_code, proc_conf = CountryCodes.get_code(proc_val)

        if not proc_code and guest.nacionalidad and guest.nacionalidad.value:
            # Inferir desde nacionalidad
            proc_code = guest.nacionalidad.value
            proc_conf = Confidence.LOW
            guest.warnings.append("Procedencia inferida desde nacionalidad")

        # Determinar valor y confianza de procedencia
        proc_value = proc_code if proc_code else (guest.nacionalidad.value if guest.nacionalidad else "")
        proc_final_conf = proc_conf if proc_conf != Confidence.NONE else Confidence.LOW
        guest.procedencia = FieldResult(proc_value, proc_final_conf)

        # === DESTINO ===
        dest_val = self._get_value(row, 'destino')

        # Primero verificar si es una ciudad colombiana (ej: "Medellín", "Bogotá")
        dest_code, dest_conf = ColombianCities.get_colombia_code_if_city(dest_val)

        # Si no es ciudad colombiana, buscar como país
        if not dest_code:
            dest_code, dest_conf = CountryCodes.get_code(dest_val)

        # Default: Colombia (169) si no se detectó destino
        dest_value = dest_code if dest_code else "169"
        dest_final_conf = dest_conf if dest_conf != Confidence.NONE else Confidence.LOW
        guest.destino = FieldResult(dest_value, dest_final_conf)

        # === VALIDACIÓN FINAL ===
        required_fields = [
            ('documento', guest.documento),
            ('nombres', guest.nombres),
            ('primer_apellido', guest.primer_apellido),
            ('nacionalidad', guest.nacionalidad),
            ('fecha_movimiento', guest.fecha_movimiento),
            ('fecha_nacimiento', guest.fecha_nacimiento),
        ]

        for field_name, field_result in required_fields:
            if not field_result or not field_result.value:
                guest.errors.append(f"Falta {field_name}")

        guest.is_valid = len(guest.errors) == 0

        return guest

    def convert(self, df: pd.DataFrame, movement_type: str = "E") -> Tuple[List[str], Dict]:
        """
        Convierte DataFrame a formato SIRE.

        Args:
            df: DataFrame con datos
            movement_type: "E" para entrada, "S" para salida

        Returns:
            Tuple[líneas_sire, estadísticas]
        """
        # Detectar columnas
        self.column_map = ColumnDetector.detect_columns(df)

        logger.info("Columnas detectadas:")
        for field, (col, conf) in self.column_map.items():
            logger.info(f"  {field} -> '{col}' ({conf.value})")

        lines = []
        seen_keys = set()

        self.stats = {
            "total": len(df),
            "valid": 0,
            "skipped": 0,
            "colombianos": 0,
            "duplicados": 0,
            "inferidos": 0,
        }
        self.errors = []
        self.warnings = []

        for idx, row in df.iterrows():
            try:
                guest = self._process_guest(row, idx, movement_type)

                if guest is None:  # Colombiano
                    self.stats["colombianos"] += 1
                    continue

                if not guest.is_valid:
                    self.stats["skipped"] += 1
                    for err in guest.errors:
                        self.errors.append(f"Fila {guest.row_number}: {err}")
                    continue

                # Verificar duplicados
                unique_key = f"{guest.documento.value}|{guest.fecha_movimiento.value}|{movement_type}"
                if unique_key in seen_keys:
                    self.stats["duplicados"] += 1
                    continue
                seen_keys.add(unique_key)

                # Construir línea SIRE
                fields = [
                    self.hotel_code,
                    self.city_code,
                    guest.tipo_documento.value if guest.tipo_documento else "3",
                    guest.documento.value,
                    guest.nacionalidad.value if guest.nacionalidad else "",
                    guest.primer_apellido.value if guest.primer_apellido else "",
                    guest.segundo_apellido.value if guest.segundo_apellido else "",
                    guest.nombres.value if guest.nombres else "",
                    movement_type,
                    guest.fecha_movimiento.value if guest.fecha_movimiento else "",
                    guest.procedencia.value if guest.procedencia else "",
                    guest.destino.value if guest.destino else "169",
                    guest.fecha_nacimiento.value if guest.fecha_nacimiento else "",
                ]

                lines.append("\t".join(fields))
                self.stats["valid"] += 1

                # Registrar warnings
                for warn in guest.warnings:
                    self.warnings.append(f"Fila {guest.row_number}: {warn}")

            except Exception as e:
                self.stats["skipped"] += 1
                self.errors.append(f"Fila {idx + 2}: Error inesperado - {str(e)}")
                logger.error(f"Error procesando fila {idx + 2}: {e}")

        return lines, self.stats

    def save_file(self, lines: List[str], output_dir: str = ".") -> str:
        """Guarda el archivo SIRE."""
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M")
        filename = f"reporte_sire_{timestamp}.txt"
        output_path = os.path.join(output_dir, filename)

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write("\n".join(lines))

        logger.info(f"Archivo guardado: {output_path} ({len(lines)} registros)")
        return output_path

    def get_report(self) -> str:
        """Genera un reporte de la conversión."""
        report = []
        report.append("=" * 60)
        report.append("REPORTE DE CONVERSIÓN SIRE")
        report.append("=" * 60)
        report.append("")
        report.append(f"Total registros procesados: {self.stats['total']}")
        report.append(f"Registros válidos:          {self.stats['valid']}")
        report.append(f"Colombianos excluidos:      {self.stats['colombianos']}")
        report.append(f"Duplicados removidos:       {self.stats['duplicados']}")
        report.append(f"Campos inferidos:           {self.stats['inferidos']}")
        report.append(f"Registros omitidos:         {self.stats['skipped']}")

        if self.warnings:
            report.append("")
            report.append("ADVERTENCIAS:")
            for warn in self.warnings[:20]:  # Limitar a 20
                report.append(f"  ⚠ {warn}")
            if len(self.warnings) > 20:
                report.append(f"  ... y {len(self.warnings) - 20} más")

        if self.errors:
            report.append("")
            report.append("ERRORES:")
            for err in self.errors[:20]:
                report.append(f"  ✗ {err}")
            if len(self.errors) > 20:
                report.append(f"  ... y {len(self.errors) - 20} más")

        report.append("")
        report.append("=" * 60)

        return "\n".join(report)


# Función de conveniencia para uso desde línea de comandos
def convert_file(input_path: str, hotel_code: str, city_code: str = "5001",
                 movement_type: str = "E", output_dir: str = ".") -> str:
    """
    Convierte un archivo Police Report a formato SIRE.

    Args:
        input_path: Ruta al archivo de entrada
        hotel_code: Código del establecimiento
        city_code: Código de ciudad (default: 5001)
        movement_type: "E" para entrada, "S" para salida
        output_dir: Directorio de salida

    Returns:
        Ruta del archivo generado
    """
    converter = SireConverter(hotel_code, city_code)
    df = converter.read_file(input_path)
    lines, stats = converter.convert(df, movement_type)

    print(converter.get_report())

    if lines:
        return converter.save_file(lines, output_dir)
    else:
        print("No se generaron registros válidos")
        return ""


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 3:
        print("Uso: python sire_converter.py <archivo> <codigo_hotel> [codigo_ciudad] [E|S] [output_dir]")
        sys.exit(1)

    input_file = sys.argv[1]
    hotel = sys.argv[2]
    city = sys.argv[3] if len(sys.argv) > 3 else "5001"
    mov = sys.argv[4] if len(sys.argv) > 4 else "E"
    out = sys.argv[5] if len(sys.argv) > 5 else "."

    result = convert_file(input_file, hotel, city, mov, out)

    if result:
        print(f"\n✓ Archivo generado: {result}")
    else:
        sys.exit(1)
