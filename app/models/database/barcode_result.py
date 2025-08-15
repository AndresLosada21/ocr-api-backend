# app/models/database/barcode_result.py
"""
Modelo para armazenar resultados detalhados de leitura de códigos de barras.
Complementa a tabela processing_jobs com dados específicos de barcodes.
"""
from sqlalchemy import Column, String, Text, Integer, Float, Boolean, JSON, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from typing import Dict, Any, List, Optional

from app.models.database.base import BaseModel

class BarcodeResult(BaseModel):
    """
    Modelo para resultados detalhados de leitura de códigos de barras.
    Armazena informações específicas sobre cada código encontrado.
    """
    
    __tablename__ = "barcode_results"
    __table_args__ = {
        'comment': 'Resultados detalhados de leitura de códigos de barras'
    }
    
    # ======================
    # RELATIONSHIP
    # ======================
    job_id = Column(
        UUID(as_uuid=True),
        ForeignKey("processing_jobs.id", ondelete="CASCADE"),
        nullable=False,
        comment="ID do job de processamento relacionado"
    )
    
    # ======================
    # BARCODE DATA
    # ======================
    barcode_data = Column(
        Text,
        nullable=False,
        comment="Dados decodificados do código de barras"
    )
    
    barcode_type = Column(
        String(50),
        nullable=False,
        comment="Tipo do código: EAN13, CODE128, CODE39, etc."
    )
    
    barcode_format = Column(
        String(20),
        nullable=True,
        comment="Formato específico detectado"
    )
    
    data_length = Column(
        Integer,
        nullable=False,
        comment="Comprimento dos dados decodificados"
    )
    
    # ======================
    # POSITION AND SIZE
    # ======================
    bbox = Column(
        JSON,
        nullable=True,
        comment="Coordenadas da bounding box [x, y, width, height]"
    )
    
    center_x = Column(
        Integer,
        nullable=True,
        comment="Coordenada X do centro do código"
    )
    
    center_y = Column(
        Integer,
        nullable=True,
        comment="Coordenada Y do centro do código"
    )
    
    width = Column(
        Integer,
        nullable=True,
        comment="Largura do código em pixels"
    )
    
    height = Column(
        Integer,
        nullable=True,
        comment="Altura do código em pixels"
    )
    
    area_pixels = Column(
        Integer,
        nullable=True,
        comment="Área total ocupada pelo código"
    )
    
    # ======================
    # QUALITY METRICS
    # ======================
    quality_score = Column(
        Float,
        nullable=True,
        comment="Score de qualidade da leitura (0-1)"
    )
    
    quality_description = Column(
        String(20),
        nullable=True,
        comment="Descrição da qualidade: excellent, good, fair, poor"
    )
    
    read_confidence = Column(
        Float,
        nullable=True,
        comment="Confiança na leitura dos dados (0-1)"
    )
    
    decode_attempts = Column(
        Integer,
        default=1,
        nullable=False,
        comment="Número de tentativas de decodificação"
    )
    
    # ======================
    # VALIDATION
    # ======================
    checksum_valid = Column(
        Boolean,
        nullable=True,
        comment="Se o checksum do código é válido"
    )
    
    checksum_value = Column(
        String(10),
        nullable=True,
        comment="Valor do checksum calculado"
    )
    
    format_valid = Column(
        Boolean,
        default=True,
        nullable=False,
        comment="Se o formato do código está correto"
    )
    
    data_valid = Column(
        Boolean,
        default=True,
        nullable=False,
        comment="Se os dados são válidos para o tipo"
    )
    
    # ======================
    # PROCESSING DETAILS
    # ======================
    decoder_used = Column(
        String(50),
        nullable=True,
        comment="Biblioteca/decoder utilizado (pyzbar, etc.)"
    )
    
    orientation = Column(
        Float,
        nullable=True,
        comment="Orientação do código em graus"
    )
    
    skew_angle = Column(
        Float,
        nullable=True,
        comment="Ângulo de inclinação detectado"
    )
    
    preprocessing_applied = Column(
        JSON,
        nullable=True,
        comment="Preprocessamentos aplicados para melhorar leitura"
    )
    
    # ======================
    # CONTENT ANALYSIS
    # ======================
    content_type = Column(
        String(30),
        nullable=True,
        comment="Tipo de conteúdo: product, isbn, serial, custom, etc."
    )
    
    country_code = Column(
        String(5),
        nullable=True,
        comment="Código do país (para EAN/UPC)"
    )
    
    manufacturer_code = Column(
        String(10),
        nullable=True,
        comment="Código do fabricante (para EAN/UPC)"
    )
    
    product_code = Column(
        String(10),
        nullable=True,
        comment="Código do produto (para EAN/UPC)"
    )
    
    check_digit = Column(
        String(5),
        nullable=True,
        comment="Dígito verificador"
    )
    
    # ======================
    # METADATA
    # ======================
    is_gs1_compliant = Column(
        Boolean,
        nullable=True,
        comment="Se o código segue padrões GS1"
    )
    
    symbology_details = Column(
        JSON,
        nullable=True,
        comment="Detalhes específicos da simbologia"
    )
    
    parsing_errors = Column(
        JSON,
        nullable=True,
        comment="Erros encontrados durante parsing"
    )
    
    # ======================
    # RELATIONSHIP
    # ======================
    job = relationship(
        "ProcessingJob",
        back_populates="barcode_results",
        lazy="select"
    )
    
    def __init__(self, **kwargs):
        """Inicializa resultado de barcode."""
        super().__init__(**kwargs)
        self._calculate_derived_fields()
    
    def _calculate_derived_fields(self) -> None:
        """Calcula campos derivados automaticamente."""
        # Calcular comprimento dos dados
        if self.barcode_data:
            self.data_length = len(self.barcode_data)
        
        # Calcular posição central e área se bbox disponível
        if self.bbox and len(self.bbox) >= 4:
            x, y, w, h = self.bbox
            self.center_x = int(x + w / 2)
            self.center_y = int(y + h / 2)
            self.width = int(w)
            self.height = int(h)
            self.area_pixels = int(w * h)
        
        # Analisar conteúdo
        self._analyze_content()
    
    def _analyze_content(self) -> None:
        """Analisa o conteúdo do código para extrair informações."""
        if not self.barcode_data:
            return
        
        data = self.barcode_data.strip()
        
        # Determinar tipo de conteúdo
        if self.barcode_type in ["EAN13", "EAN8", "UPC_A", "UPC_E"]:
            self._analyze_ean_upc(data)
        elif self.barcode_type in ["CODE128", "CODE39"]:
            self._analyze_alphanumeric(data)
        elif data.isdigit():
            self.content_type = "numeric"
        elif data.isalnum():
            self.content_type = "alphanumeric"
        else:
            self.content_type = "mixed"
    
    def _analyze_ean_upc(self, data: str) -> None:
        """Analisa códigos EAN/UPC."""
        self.content_type = "product"
        
        if len(data) == 13 and data.isdigit():  # EAN13
            self.country_code = data[:3]
            self.manufacturer_code = data[3:7]
            self.product_code = data[7:12]
            self.check_digit = data[12]
            self._validate_ean13_checksum(data)
        elif len(data) == 12 and data.isdigit():  # UPC-A
            self.manufacturer_code = data[:6]
            self.product_code = data[6:11]
            self.check_digit = data[11]
            self._validate_upc_checksum(data)
        elif len(data) == 8 and data.isdigit():  # EAN8
            self.country_code = data[:2]
            self.manufacturer_code = data[2:5]
            self.product_code = data[5:7]
            self.check_digit = data[7]
    
    def _analyze_alphanumeric(self, data: str) -> None:
        """Analisa códigos alfanuméricos."""
        if data.upper().startswith("ISBN"):
            self.content_type = "isbn"
        elif data.upper().startswith("SN"):
            self.content_type = "serial"
        elif data.isdigit():
            self.content_type = "numeric"
        else:
            self.content_type = "custom"
    
    def _validate_ean13_checksum(self, data: str) -> None:
        """Valida checksum de EAN13."""
        if len(data) != 13 or not data.isdigit():
            self.checksum_valid = False
            return
        
        # Algoritmo de validação EAN13
        odd_sum = sum(int(data[i]) for i in range(0, 12, 2))
        even_sum = sum(int(data[i]) for i in range(1, 12, 2))
        total = odd_sum + (even_sum * 3)
        check_digit = (10 - (total % 10)) % 10
        
        self.checksum_value = str(check_digit)
        self.checksum_valid = (check_digit == int(data[12]))
    
    def _validate_upc_checksum(self, data: str) -> None:
        """Valida checksum de UPC."""
        if len(data) != 12 or not data.isdigit():
            self.checksum_valid = False
            return
        
        # Algoritmo de validação UPC
        odd_sum = sum(int(data[i]) for i in range(0, 11, 2))
        even_sum = sum(int(data[i]) for i in range(1, 11, 2))
        total = (odd_sum * 3) + even_sum
        check_digit = (10 - (total % 10)) % 10
        
        self.checksum_value = str(check_digit)
        self.checksum_valid = (check_digit == int(data[11]))
    
    def set_quality_from_score(self, score: float) -> None:
        """
        Define descrição de qualidade baseada no score.
        
        Args:
            score: Score de qualidade (0-1)
        """
        self.quality_score = score
        
        if score >= 0.9:
            self.quality_description = "excellent"
        elif score >= 0.7:
            self.quality_description = "good"
        elif score >= 0.5:
            self.quality_description = "fair"
        else:
            self.quality_description = "poor"
    
    def get_product_info(self) -> Optional[Dict[str, Any]]:
        """
        Retorna informações do produto se for um código de produto.
        
        Returns:
            Dicionário com informações do produto ou None
        """
        if self.content_type != "product":
            return None
        
        return {
            "barcode_type": self.barcode_type,
            "full_code": self.barcode_data,
            "country_code": self.country_code,
            "manufacturer_code": self.manufacturer_code,
            "product_code": self.product_code,
            "check_digit": self.check_digit,
            "checksum_valid": self.checksum_valid,
            "is_gs1_compliant": self.is_gs1_compliant
        }
    
    def get_summary(self) -> Dict[str, Any]:
        """
        Retorna resumo das informações do código de barras.
        
        Returns:
            Dicionário com resumo dos dados
        """
        return {
            "barcode_type": self.barcode_type,
            "data": self.barcode_data,
            "data_length": self.data_length,
            "content_type": self.content_type,
            "quality": {
                "score": self.quality_score,
                "description": self.quality_description,
                "confidence": self.read_confidence
            },
            "validation": {
                "checksum_valid": self.checksum_valid,
                "format_valid": self.format_valid,
                "data_valid": self.data_valid
            },
            "position": {
                "center": [self.center_x, self.center_y] if self.center_x else None,
                "size": [self.width, self.height] if self.width else None,
                "area": self.area_pixels
            },
            "processing": {
                "decoder": self.decoder_used,
                "orientation": self.orientation,
                "attempts": self.decode_attempts
            }
        }
    
    def to_dict(self, include_details: bool = True) -> Dict[str, Any]:
        """
        Converte para dicionário com opção de incluir detalhes.
        
        Args:
            include_details: Se deve incluir campos detalhados
            
        Returns:
            Dicionário com dados do modelo
        """
        exclude_fields = set()
        if not include_details:
            exclude_fields.update([
                "symbology_details", "parsing_errors", "preprocessing_applied"
            ])
        
        return super().to_dict(exclude_fields=exclude_fields)
    
    def __repr__(self) -> str:
        """Representação string do resultado de barcode."""
        return f"<BarcodeResult(job_id={self.job_id}, type={self.barcode_type}, data='{self.barcode_data[:20]}...')>"